import sys
import os
from pathlib import Path
import io
from base64 import b64decode, b64encode

from cryptography.hazmat.primitives import hashes, hmac
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.backends import default_backend
from nacl.bindings import (crypto_kx_client_session_keys,
                           crypto_kx_server_session_keys,
                           crypto_aead_chacha20poly1305_ietf_encrypt,
                           crypto_aead_chacha20poly1305_ietf_decrypt)
from nacl.exceptions import CryptoError
from nacl.public import PrivateKey

# from code_api.crypt4gh_altered.crypt4gh import lib, header
# import code_api.crypt4gh_altered.crypt4gh.keys.c4gh as keys
# from code_api.crypt4gh_altered.crypt4gh.keys.c4gh import MAGIC_WORD, parse_private_key
from code_api.crypt4gh.crypt4gh import lib, header, keys

from code_api.dp_exceptions import HashException, EncryptionError

SEGMENT_SIZE = 65536
MAGIC_NUMBER = b'crypt4gh'
VERSION = 1
CIPHER_DIFF = 28
CIPHER_SEGMENT_SIZE = SEGMENT_SIZE + CIPHER_DIFF


class Crypt4GHKey:

    def __init__(self, name="", tempdir=""):

        print("tempdir: ", tempdir)
        secpath = tempdir / Path(f"{name}.sec")
        pubpath = tempdir / Path(f"{name}.pub")
        keys.c4gh.generate(seckey=secpath,
                           pubkey=pubpath)

        self.pubkey = keys.get_public_key(pubpath)
        self.seckey = keys.get_private_key(secpath, callback=None)

        # self.public, self.secret = keys.generate()

        # # correct private key
        # lines_pub = self.public.splitlines()
        # assert(b'CRYPT4GH' in lines_pub[0])
        # self.public_parsed = b64decode(b''.join(lines_pub[1:-1]))

        # # correct secret key
        # lines = self.secret.splitlines()
        # assert(lines[0].startswith(b'-----BEGIN ') and
        #        lines[-1].startswith(b'-----END '))
        # data = b64decode(b''.join(lines[1:-1]))

        # stream = io.BytesIO(data)

        # magic_word = stream.read(len(MAGIC_WORD))
        # if magic_word == MAGIC_WORD:  # it's a crypt4gh key
        #     self.secret_decrypted = parse_private_key(stream)

    def encrypt(self, recip_pubkey, infile, outfile, offset=0, span=None):
        '''Encrypt infile into outfile, using the list of keys.


        It fast-forwards to `offset` and encrypts until
        a total of `span` bytes is reached (or to EOF if `span` is None)

        This produces a Crypt4GH file without edit list.
        '''

        # Preparing the encryption engine
        encryption_method = 0  # only choice for this version
        session_key = os.urandom(32)  # we use one session key for all blocks
        print("Session key encryption: ", session_key)

        # Output the header
        header_content = header.make_packet_data_enc(encryption_method,
                                                     session_key)
        header_packets = header.encrypt(header_content, self.secret_decrypted,
                                        recip_pubkey)
        header_bytes = header.serialize(header_packets)

        print("Header bytes: ", header_bytes)

        with outfile.open(mode='wb+') as of:
            of.write(header_bytes)

        segment = bytearray(SEGMENT_SIZE)

        # The whole file
        with infile.open(mode='rb') as inf:
            while True:
                segment_len = inf.readinto(segment)

                if segment_len == 0:  # finito
                    break

                if segment_len < SEGMENT_SIZE:  # not a full segment
                    # to discard the bytes from the previous segments
                    data = bytes(segment[:segment_len])
                    self._encrypt_segment(data, outfile, session_key)
                    break

                data = bytes(segment)  # this is a full segment
                self._encrypt_segment(data, outfile, session_key)

        return True

    def _encrypt_segment(self, data, outfile, key):
        '''Utility function to generate a nonce, encrypt data with Chacha20, and authenticate it with Poly1305.'''

        nonce = os.urandom(12)
        encrypted_data = crypto_aead_chacha20poly1305_ietf_encrypt(
            data, None, nonce, key)  # no add

        # after producing the segment, so we don't start outputing when an error occurs
        with outfile.open(mode='ab') as of:
            of.write(nonce)
            of.write(encrypted_data)

    def prep_upload(self, file: str, recip_pub, tempdir, path_from_base):
        '''Prepares the files for upload'''

        tempdir_files = tempdir[1]  # Path to temporary delivery file folder

        filedir = None
        if isinstance(tempdir_files, Path):
            try:
                filedir = tempdir_files / path_from_base
                original_umask = os.umask(0)
                filedir.mkdir(parents=True)
            except IOError as ioe:
                sys.exit(f"Could not create folder {filedir}: {ioe}")
            finally:
                os.umask(original_umask)

        # hash
        _, checksum = gen_hmac(file=file)

        # encrypt
        encrypted_file = filedir / Path(file.name + ".c4gh")
        try:
            original_umask = os.umask(0)
            with file.open(mode='rb') as infile:
                with encrypted_file.open(mode='ab+') as outfile:
                    lib.encrypt(keys=[(0, self.seckey, recip_pub)],
                                infile=infile,
                                outfile=outfile)
            # self.encrypt(recip_keys, file, encrypted_file)
        except EncryptionError as ee:
            sys.exit(f"Encryption of file {file} failed: {ee}")
        finally:
            os.umask(original_umask)

        return file, encrypted_file, checksum

    def parse_header(self, infile):

        buf = bytearray(16)
        with infile.open(mode='rb') as file:
            if file.readinto(buf) != 16:
                raise ValueError('Header too small')

            magic_number = bytes(buf[:8])  # 8 bytes
            if magic_number != MAGIC_NUMBER:
                raise ValueError('Not a CRYPT4GH formatted file')

            # Version, 4 bytes
            version = int.from_bytes(bytes(buf[8:12]), byteorder='little')
            if version != VERSION:  # only version 1, so far
                raise ValueError('Unsupported CRYPT4GH version')

            # Packets count
            packets_count = int.from_bytes(
                bytes(buf[12:16]), byteorder='little')

            # Spit out one packet at a time
            for i in range(packets_count):
                encrypted_packet_len = int.from_bytes(
                    file.read(4), byteorder='little') - 4  # include packet_len itself
                if encrypted_packet_len < 0:
                    raise ValueError(
                        f'Invalid packet length {encrypted_packet_len}')
                encrypted_packet_data = file.read(encrypted_packet_len)
                if len(encrypted_packet_data) < encrypted_packet_len:
                    raise ValueError('Packet {} too small'.format(i))
                yield encrypted_packet_data

    def decrypt_header_packet(self, encrypted_packet, sender_pubkey):

        packet_encryption_method = int.from_bytes(
            encrypted_packet[:4], byteorder='little')
        print("Packet encryption method: ", packet_encryption_method)

        if packet_encryption_method != 0:
            print("WRONG METHOD")  # not a corresponding key anyway

        try:
            privkey = self.secret_decrypted
            return self.decrypt_X25519_Chacha20_Poly1305(encrypted_packet[4:], privkey, sender_pubkey=sender_pubkey)
        except CryptoError as tag:
            sys.exit(tag)
            # LOG.error('Packet Decryption failed: %s', tag)
        # Any other error, like (IndexError, TypeError, ValueError)
        except Exception as e:
            sys.exit(e)
            # LOG.error('Not a X25519 key: ignoring | %s', e)
            # try the next one

    def decrypt_X25519_Chacha20_Poly1305(self, encrypted_part, privkey, sender_pubkey=None):

        peer_pubkey = encrypted_part[:32]
        print("Peer public key: ", peer_pubkey)
        if sender_pubkey and sender_pubkey != peer_pubkey:
            raise ValueError("Invalid Peer's Public Key")

        nonce = encrypted_part[32:44]
        packet_data = encrypted_part[44:]

        # X25519 shared key
        # slightly inefficient, but working
        pubkey = bytes(PrivateKey(privkey).public_key)
        # print("Shared key: ", pubkey)
        shared_key, _ = crypto_kx_client_session_keys(
            pubkey, privkey, peer_pubkey)
        print("Shared key: ", shared_key)
        # Chacha20_Poly1305
        # no add
        return crypto_aead_chacha20poly1305_ietf_decrypt(packet_data, None, nonce, shared_key)

    def limited_output(self, outfile, offset=0, limit=None):
        '''Generator that receives clear text and does not process more than limit bytes (if limit is not None).

        Raises ProcessingOver if the limit is reached'''

        with outfile.open(mode='wb') as decrypted_file:
            while True:
                data = yield
                data_len = len(data)

                if data_len < offset:  # not enough data to chop off
                    offset -= data_len
                    continue  # ignore output

                if limit is None:
                    # no copying here if offset=0!
                    decrypted_file.write(data[offset:])
                else:

                    if limit < (data_len - offset):  # should stop early
                        decrypted_file.write(data[offset:limit+offset])
                        raise ProcessingOver()
                    else:
                        # no copying here if offset=0!
                        decrypted_file.write(data[offset:])
                        limit -= (data_len - offset)

                offset = 0  # reset offset

    def cipher_chunker(self, f, size):
        with f.open(mode='rb') as f:
            while True:
                ciphersegment = f.read(size)
                ciphersegment_len = len(ciphersegment)
                if ciphersegment_len == 0:
                    break  # We were at the last segment. Exits the loop
                assert(ciphersegment_len > CIPHER_DIFF)
                yield ciphersegment

    def body_decrypt(self, infile, session_keys, output, offset):
        """Decrypt the whole data portion.

        We fast-forward if offset >= SEGMENT_SIZE.
        We decrypt until the first one occurs:
        * `output` reaches its end
        * `infile` reaches its end."""

        # In this case, we try to fast-forward, and adjust the offset
        # if offset >= SEGMENT_SIZE:
        #     start_segment, offset = divmod(offset, SEGMENT_SIZE)
        #     start_ciphersegment = start_segment * CIPHER_SEGMENT_SIZE
        #     infile.seek(start_ciphersegment, io.SEEK_CUR)  # move forward

        try:
            for ciphersegment in self.cipher_chunker(infile, CIPHER_SEGMENT_SIZE):
                segment = self.decrypt_block(ciphersegment, session_keys)
                output.send(segment)
        except ProcessingOver:  # output raised it
            pass

    def decrypt_block(self, ciphersegment, session_keys):
        # Trying the different session keys (via the cipher objects)
        # Note: we could order them and if one fails, we move it at the end of the list
        # So... LRU solution. For now, try them as they come.
        nonce = ciphersegment[:12]
        print("Nonce: ", nonce)
        data = ciphersegment[12:]
        print("Data: ", data)
        for key in session_keys:
            print("Key: ", key)
            try:
                # no add, and break the loop
                return crypto_aead_chacha20poly1305_ietf_decrypt(data, None, nonce, key)
            except CryptoError as tag:
                print("---> ", tag)
                print(sys.exc_info()[0])
                raise
                # LOG.error('Decryption failed: %s', tag)
        else:  # no cipher worked: Bark!
            raise ValueError('Could not decrypt that block')

    def decrypt(self, infile, outfile, sender_keys):
        '''Decrypt infile into outfile, using a given set of keys.

        If sender_pubkey is specified, it verifies the provenance of the header.

        If no header packet is decryptable, it raises a ValueError
        '''

        # assert( # Checking the range
        #     isinstance(offset, int)
        #     and offset >= 0
        #     and (
        #         span is None
        #         or
        #         (isinstance(span, int) and span > 0)
        #     )
        # )

        # session_keys, edit_list = header.deconstruct(infile, keys, sender_pubkey=sender_pubkey)

        encrypted_header_packet_stream = self.parse_header(infile)
        decrypted_packets = []
        ignored_packets = []
        for packet in encrypted_header_packet_stream:
            print("Packet from stream: ", packet)

            decrypted_packet = self.decrypt_header_packet(
                packet, sender_pubkey=sender_keys.public_parsed)
            print("Decrypted_packet: ", decrypted_packet)
            if decrypted_packet is None:  # They all failed
                ignored_packets.append(packet)
            else:
                decrypted_packets.append(decrypted_packet)

        print("Decrypted packets: ", decrypted_packets)
        print("Ignored packets: ", ignored_packets)

        data_packets, edit_packet = header.partition_packets(decrypted_packets)
        print("Data packets: ", data_packets)
        # Parse returns the session key (since it should be method 0)
        session_keys = [header.parse_enc_packet(
            packet) for packet in data_packets]
        print("Session keys: ", session_keys)
        edit_list = header.parse_edit_list_packet(
            edit_packet) if edit_packet else None
        print("Edit list: ", edit_list)

        # Infile in now positioned at the beginning of the data portion

        # Generator to slice the output
        output = self.limited_output(outfile=outfile)
        next(output)  # start it

        if edit_list is None:
            # No edit list: decrypt all segments until the end
            self.body_decrypt(infile, session_keys, output, 0)
            # We could use body_decrypt_parts but there is an inner buffer, and segments might not be aligned
        else:
            print("error")
            # Edit list: it drives which segments is decrypted
            # body_decrypt_parts(infile, session_keys, output, edit_list=list(edit_list))

        # LOG.info('Decryption Over')

    def finish_download(self, file, sender_keys):
        '''Finishes file download, including decryption and
        checksum generation'''

        print(f"File to decrypt: {file}")

        if isinstance(file, Path):
            try:
                dec_file = Path(str(file).split(
                    file.name)[0]) / Path(file.stem)
                print(dec_file)
            except Exception:
                sys.exit("FEL")
            finally:
                original_umask = os.umask(0)
                with file.open(mode='rb') as infile:
                    with dec_file.open(mode='ab+') as outfile:
                        lib.decrypt(keys=[(0, self.seckey, sender_keys)],
                                    infile=infile,
                                    outfile=outfile)

        _, checksum = gen_hmac(file=dec_file)
        _, checksum_orig = gen_hmac(file=Path(
            "/Users/inaod568/repos/Data-Delivery-Portal/files/testfolder/testfile_05.fna"))

        print(checksum)
        print(checksum_orig)
        print(
            f"Decryption successful - original and decrypted file identical: {checksum==checksum_orig}")


def secure_password_hash(password_settings: str,
                         password_entered: str) -> (str):
    '''Generates secure password hash.

    Args:
            password_settings:  String containing the salt, length of hash,
                                n-exponential, r and p variables.
                                Taken from database. Separated by '$'.
            password_entered:   The user-specified password.

    Returns:
            str:    The derived hash from the user-specified password.

    '''

    settings = password_settings.split("$")
    for i in [1, 2, 3, 4]:
        settings[i] = int(settings[i])

    kdf = Scrypt(salt=bytes.fromhex(settings[0]),
                 length=settings[1],
                 n=2**settings[2],
                 r=settings[3],
                 p=settings[4],
                 backend=default_backend())

    return (kdf.derive(password_entered.encode('utf-8'))).hex()


def gen_hmac(file) -> (Path, str):
    '''Generates a HMAC for a file

    Args:
        file: Path to hash

    Returns:
        tuple: File and path

            Path:   Path to file
            str:    HMAC generated for file
    '''

    file_hash = hmac.HMAC(key=b'SuperSecureChecksumKey',
                          algorithm=hashes.SHA256(),
                          backend=default_backend())
    try:
        with file.open(mode='rb') as f:
            for chunk in iter(lambda: f.read(8388608), b''):
                file_hash.update(chunk)
    except HashException as he:
        sys.exit(f"HMAC for file {str(file)} could not be generated: {he}")
    else:
        return file, file_hash.finalize().hex()


def gen_hmac_streamed(file) -> (Path, str):
    '''Generates a HMAC for a file

    Args:
        file: Path to hash

    Returns:
        tuple: File and path

            Path:   Path to file
            str:    HMAC generated for file
    '''

    try:
        with file.open(mode='rb') as f:
            for chunk in iter(lambda: f.read(8388608), b''):
                file_hash.update(chunk)
    except HashException as he:
        sys.exit(f"HMAC for file {str(file)} could not be generated: {he}")
    else:
        return file, file_hash.finalize().hex()


class ProcessingOver(Exception):
    pass

