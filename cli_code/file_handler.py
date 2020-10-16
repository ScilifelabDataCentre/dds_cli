"""
File handler.
Responsible for IO related operations, including compression, encryption, etc.
"""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import logging
import os
import pathlib
import zstandard as zstd

# Installed
from nacl.bindings import crypto_aead_chacha20poly1305_ietf_decrypt as decrypt
from nacl.bindings import crypto_aead_chacha20poly1305_ietf_encrypt as encrypt

# Own modules
from cli_code import CIPHER_SEGMENT_SIZE
from cli_code import crypto_ds
from cli_code import DIRS
from cli_code import exceptions_ds
from cli_code import SEGMENT_SIZE


###############################################################################
# GLOBAL VARIABLES ######################################### GLOBAL VARIABLES #
###############################################################################
# NOTE: Move these to other module?

# Compression formats and their file signatures
MAGIC_DICT = {
    b'\x913HF': "hap",
    b'ustar': "tar",
    b'`\xea': "arj",
    b"_\'\xa8\x89": "jar",
    b'ZOO ': "zoo",
    b'PK\x03\x04': "zip",
    b'UFA\xc6\xd2\xc1': "ufa",
    b'StuffIt ': "sit",
    b'Rar!\x1a\x07\x00': "rar v4.x",
    b'Rar!\x1a\x07\x01\x00': "rar v5",
    b'MAr0\x00': "mar",
    b'DMS!': "dms",
    b'CRUSH v': "cru",
    b'BZh': "bz2",
    b'-lh': "lha",
    b'(This fi': "hqx",
    b'!\x12': "ain",
    b'\x1a\x0b': "pak",
    b'(\xb5/\xfd': "zst"
}
MAX_FMT = max(len(x) for x in MAGIC_DICT)   # Longest signature

MAX_NONCE = 2**(12*8)   # Max mumber of nonces

###############################################################################
# Logging ########################################################### Logging #
###############################################################################

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)

###############################################################################
# IO FUNCTIONS ################################################# IO FUNCTIONS #
###############################################################################


def file_deleter(file: pathlib.Path):
    '''Delete file

    Args:
        file (Path):    Path to file

    '''

    if not file.exists():
        return

    # Try file.unlink() first (pathlib) and then os.remove(file) (os) if failed
    # Log warning - don't quit if deletion not possible
    try:
        file.unlink()
    except OSError as ose:
        LOG.warning("Failed deleting file '%s': %s.\nTrying again.",
                    file, ose)
        try:
            os.remove(file)
        except OSError as ose:
            error = f"Failed deleting file {file}: {ose}."
            LOG.warning(error)
            return True, error
        else:
            LOG.info("Deleted file '%s'", file)
    else:
        LOG.info("Deleted file '%s'", file)
        return True, ""


def file_reader(filehandler, chunk_size: int = SEGMENT_SIZE) -> (bytes):
    '''Yields the file chunk by chunk.

    Args:
        file:           Path to file
        chunk_size:     Number of bytes to read from file at a time

    Yields:
        bytes:  Data chunk of size chunk_size
    '''

    for chunk in iter(lambda: filehandler.read(chunk_size), b''):
        yield chunk


# NOTE: Merge this with decompress_file?
def file_writer(filehandler, gen, last_nonce):
    '''Writes decrypted chunks to file. Checks if last nonces match.

    Args:
        filehandler:            Filehandler to save decompressed chunks to/with
        gen:                    Generator - all decrypted chunks streamed
        last_nonce (bytes):     Last nonce found from file

    Returns:
        tuple:  Info on saved file, decryption and decompression

            bool:   True if file saved and last nonce is correct
            str:    Error message, "" if none

    '''

    nonce = b''  # Catches last nonce while decompressing decrypted chunk

    # Save chunks to file
    for nonce, chunk in gen:
        filehandler.write(chunk)

    # If reached end of file but nonces don't match - the entire file has not
    # been delivered -- error
    nonce_ok, error = check_last_nonce(filename=filehandler.name,
                                       last_nonce=last_nonce,
                                       nonce=nonce)

    return nonce_ok, error


def get_root_path(file: pathlib.Path, path_base: str = None) -> (pathlib.Path):
    '''Gets the path to the file, from the entered folder.

    Args:
        file:       Path to file
        path_base:  None if single file, folder name if in folder

    Returns:
        Path:   Path from folder to file
    '''

    fileparts = file.parts
    start_ind = fileparts.index(path_base)
    return pathlib.Path(*fileparts[start_ind:-1])


###############################################################################
# COMPRESSION ################################################### COMPRESSION #
###############################################################################
# NOTE: Move to own module/class?


def compress_file(filehandler, chunk_size: int = SEGMENT_SIZE) -> (bytes):
    '''Compresses file

    Args:
        file:           Path to file
        chunk_size:     Number of bytes to compress at a time

    Yields:
        bytes:  Compressed data chunk

    '''

    # Initiate a Zstandard compressor
    cctzx = zstd.ZstdCompressor(write_checksum=True, level=4)

    # Compress file chunk by chunk while reading
    with cctzx.stream_reader(filehandler) as compressor:
        for chunk in iter(lambda: compressor.read(chunk_size), b''):
            yield chunk


# TODO(ina): Merge this with file_writer?
def decompress_file(filehandler, gen, last_nonce: bytes) -> (bool, str):
    '''Decompresses file

    Args:
        filehandler:            Filehandler to save decompressed chunks to/with
        gen:                    Generator - all decrypted chunks streamed
        last_nonce (bytes):     Last nonce found from file

    Returns:
        tuple:  Info on saved file, decryption and decompression

            bool:   True if file saved and last nonce is correct
            str:    Error message, "" if none

    '''

    nonce = b''     # Catches last nonce while decompressing decrypted chunk

    # Decompress chunks and save to file
    dctx = zstd.ZstdDecompressor()  # Initiate a Zstandard decompressor
    with dctx.stream_writer(filehandler) as decompressor:
        for nonce, chunk in gen:
            decompressor.write(chunk)   # Write decompressed chunks to file

    # If reached end of file but nonces don't match - the entire file has not
    # been delivered -- error
    nonce_ok, error = check_last_nonce(filename=filehandler.name,
                                       last_nonce=last_nonce,
                                       nonce=nonce)

    return nonce_ok, error


def is_compressed(file: pathlib.Path) -> (bool, str):
    '''Checks for file signatures in common compression formats.

    Args:
        file (Path):   Path object to be checked.

    Returns:
        tuple:      Info on if compressed format or not.

            bool:   True if file is compressed format.
            str:    Error message, "" if no error
    '''

    error = ""  # Error message

    try:
        # Check for file signature in beginning of file
        with file.open(mode='rb') as f:
            file_start = f.read(MAX_FMT)    # Read the first x bytes
            # LOG.debug(f"file: {file}\tfile start: {file_start}")
            for magic, _ in MAGIC_DICT.items():
                if file_start.startswith(magic):    # If file signature found
                    return True, error              # File is compressed
    except OSError as e:
        LOG.warning(e)      # Log warning, do not cancel all
        error = e           # Save error message

    return False, error    # File not compressed


###############################################################################
# CRYPTO ############################################################# CRYPTO #
###############################################################################
# TODO(ina): Move to own module/class?


def aead_decrypt_chacha(file, key: bytes, iv: bytes) -> (bytes, bytes):
    '''Decrypts the file in chunks using the IETF ratified ChaCha20-Poly1305
    construction described in RFC7539.

    Args:
        file:           Filehandler to read from
        key (bytes):    Derived, shared key
        iv (bytes):     First used for encryption/decryption

    Yields:
        tuple:  Nonce and plaintext

            bytes:  Nonce used for each chunk
            bytes:  Plaintext chunk

    Raises:
        DeliverySystemException:    Failed reading of nonces

    '''

    # NOTE: Fix return error here?
    # If position not directly after first nonce, then error - fail
    if file.tell() != 12:
        raise exceptions_ds.DeliverySystemException(
            f"Reading encrypted file {file.name} failed!")

    # Variables ################################################### Variables #
    iv_int = int.from_bytes(iv, 'little')           # Transform nonce to int
    aad = None              # Associated data, unencrypted but authenticated
    # ----------------------------------------------------------------------- #

    for enc_chunk in iter(lambda: file.read(CIPHER_SEGMENT_SIZE), b''):
        # Get nonce as bytes for decryption: if the nonce is larger than the
        # max number of chunks allowed to be encrypted (safely) -- begin at 0
        nonce = (iv_int if iv_int < MAX_NONCE
                 else iv_int % MAX_NONCE).to_bytes(length=12,
                                                   byteorder='little')

        iv_int += 1  # Increment nonce

        # Decrypt and yield nonce and plaintext
        yield (nonce, decrypt(ciphertext=enc_chunk,
                              aad=aad,
                              nonce=nonce,
                              key=key))


def aead_encrypt_chacha(gen, key: bytes, iv: bytes) -> (bytes, bytes):
    '''Encrypts the file in chunks using the IETF ratified ChaCha20-Poly1305
    construction described in RFC7539.

    Args:
        gen (Generator):    Generator object, stream of file chunks
        key (bytes):        Data encryption key
        iv (bytes):         Initial nonce

    Yields:
        tuple:  The nonce for each data chunk and ciphertext

            bytes:  Nonce -- number only used once
            bytes:  Ciphertext
    '''

    # Variables ################################################### Variables #
    iv_int = int.from_bytes(iv, 'little')   # Transform nonce to int
    aad = None  # Associated data, unencrypted but authenticated
    # ----------------------------------------------------------------------- #

    for chunk in gen:
        # Get nonce as bytes for encryption: if the nonce is larger than the
        # max number of chunks allowed to be encrypted (safely) -- begin at 0
        nonce = (iv_int if iv_int < MAX_NONCE
                 else iv_int % MAX_NONCE).to_bytes(length=12,
                                                   byteorder='little')
        # LOG.debug(f"\nnonce in encryption: \t{nonce}\n")

        iv_int += 1  # Increment nonce

        # Encrypt and yield nonce and ciphertext
        yield nonce, encrypt(message=chunk,
                             aad=aad,
                             nonce=nonce,
                             key=key)


def check_last_nonce(filename: str, last_nonce: bytes, nonce: bytes) \
        -> (bool, str):
    '''Check if the nonces match and give error if they don't.

    Args:
        filename (str):     File name
        last_nonce (bytes):     Last nonce (read from end of encrypted file)
        nonce (bytes):          Nonce which decryption/decompression ended on

    Returns:
        tuple:  Info on delivery ok or not

            bool:   True if the nonces match
            str:    Error message, "" if none

    '''

    # If reached end of file but nonces don't match - the entire file has not
    # been delivered -- error
    if nonce != last_nonce:
        error = (f"File: {filename}. Nonces don't match! "
                 "File integrity compromised!")
        LOG.exception(error)
        return False, error
    else:
        return True, ""


###############################################################################
# PREP AND FINISH ########################################### PREP AND FINISH #
###############################################################################


def process_file(file: pathlib.Path, file_info: dict, peer_public) \
        -> (bool, pathlib.Path, int, bool, bytes, bytes, str):
    '''Processes the files incl compression, encryption

    Args:
        file (Path):           Path to file
        file_info (dict):      Info about file

    Returns:
        tuple: Information about finished processing

            bool:   True if processing successful
            Path:   Path to processed file
            int:    Size of processed file
            bool:   True if file compressed by the delivery system
            bytes:  Public key needed for file decryption
            bytes:  Salt needed for shared key derivation
            str:    'Error message, "" if none

    Raises:
        DeliverySystemException:    Failed processing or wrong argument format
        OSError:                    File not found or could not create tempdir

    '''

    # If file path not Path type --> quit whole execution, something wrong
    if not isinstance(file, pathlib.Path):
        emessage = f"Wrong format! {file} is not a 'Path' object."
        raise exceptions_ds.DeliverySystemException(emessage)

    # If file doesn't exist --> quit whole execution, something wrong
    if not file.exists():
        emessage = f"The path {file} does not exist!"
        raise OSError(emessage)  # Bug somewhere in code

    # Variables ################################################### Variables #
    outfile = DIRS[1] / file_info['new_file']   # Path to save processed file
    new_dir = DIRS[1] / file_info['directory_path']     # New temp subdir
    key = b''
    # ----------------------------------------------------------------------- #
    LOG.debug("Infile: '%s', Outfile: '%s'", file, outfile)

    # Encryption key ######################################### Encryption key #
    keypair = crypto_ds.ECDHKey()    # Create new ECDH key pair
    LOG.debug("\npublic key for file '%s': -- %s\n",
              file, keypair.public.public_bytes())

    # Generate shared symmetric encryption key from peer_public + pub + priv
    key, salt = keypair.generate_encryption_key(peer_public=peer_public)
    LOG.debug("file: %s\n\tprivate: %s, \tpublic: %s (%s), "
              "\tderived, shared symmetric: %s (%s)", file, keypair.private,
              keypair.public, type(keypair.public), key, len(key))
    # ----------------------------------------------------------------------- #

    # Create new temporary subdir if doesn't exist
    if not new_dir.exists():
        try:
            new_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            error = f"File: {file} - Failed creating tempdir '{new_dir}': {e}"
            LOG.exception(error)
            return False, pathlib.Path(""), 0, False, "", "", error

    # PROCESSING START ##################################### PROCESSING START #
    try:
        original_umask = os.umask(0)  # User file-creation mode mask
        with file.open(mode='rb') as f:

            # Check if to compress or read
            func = file_reader if file_info['compressed'] else compress_file

            # Compression ###### If not already compressed ###### Compression #
            chunk_stream = func(filehandler=f)

            # Encryption ######################################### Encryption #
            with outfile.open(mode='wb+') as outf:
                # Generate initial nonce and save to file
                iv_bytes = os.urandom(12)
                outf.write(iv_bytes)
                LOG.debug("File: '%s' IV: %s", file, iv_bytes)

                # Encrypt and save ciphertext (not nonces) to file
                nonce = b''     # Catches the nonces
                for nonce, ciphertext in aead_encrypt_chacha(gen=chunk_stream,
                                                             key=key,
                                                             iv=iv_bytes):
                    outf.write(ciphertext)

                # Save last nonce to end of file
                outf.write(nonce)
                LOG.debug("File: '%s', last nonce:\t%s\n", file, nonce)

    except exceptions_ds.DeliverySystemException as dse:
        error = f"File: {file}, Processig failed! {dse}"
        LOG.exception(error)
        return False, outfile, 0, False, "", "", error
    else:
        LOG.info("File: '%s', Processing successful! "
                 "Encrypted file saved at '%s'", file, outfile)
        # Info on if delivery system compressed or not
        ds_compressed = False if file_info['compressed'] else True
    finally:
        os.umask(original_umask)    # Remove mask

    # PROCESSING FINISHED ------------------------------- PROCESSING FINISHED #

    return (True, outfile, outfile.stat().st_size, ds_compressed,
            keypair.public_to_hex(), salt.hex().upper(), "")


def reverse_processing(file: str, file_info: dict, keys: tuple) \
        -> (bool, str, str):
    '''Decrypts and decompresses file (if DS compressed)

    Args:
        file (str):         Path to file
        file_info (dict):   Info on file
        keys (tuple):       Project specific ECDH keys required for decryption
                            Format: (public, private)

    Returns:
        tuple:  Info on finalizing delivery

            bool:   True if decryption etc successful
            str:    Decrypted file
            str:    Error message, "" if none

    '''

    # Variables ################################################### Variables #
    infile = file_info['new_file']                      # Downloaded file
    outfile = infile.parent / \
        pathlib.Path(infile.stem).stem    # Finalized file path
    error = ""
    # ----------------------------------------------------------------------- #
    LOG.debug("Infile: %s, Outfile: %s", infile, outfile)

    # Encryption key ######################################### Encryption key #
    # Get keys for decryption
    peer_public = bytes.fromhex(file_info['public_key'])  # File public enc key
    keypair = crypto_ds.ECDHKey(keys=keys)          # Project specific key pair
    LOG.debug("public key peer: %s\npublic key peer: %s",
              peer_public, peer_public.hex().upper())

    # Derive shared symmetric key
    salt = file_info['salt']                # Salt to generate same shared key
    key, _ = keypair.generate_encryption_key(peer_public=peer_public,
                                             salt_=salt)
    LOG.debug("file: %s\n\tprivate: %s, \tpublic: %s (%s), "
              "\tderived, shared symmetric: %s (%s)", file, keypair.private,
              keypair.public, type(keypair.public), key, len(key))

    # "Delete" private key
    keypair.del_priv_key()
    # ----------------------------------------------------------------------- #

    # START ########################################################### START #
    try:
        original_umask = os.umask(0)  # User file-creation mode mask
        with infile.open(mode='rb+') as f:
            # Get last nonce
            f.seek(-12, os.SEEK_END)
            last_nonce = f.read(12)

            # Remove last nonce from file
            f.seek(-12, os.SEEK_END)
            f.truncate()

            # Jump back to beginning and get first nonce
            f.seek(0)
            first_nonce = f.read(12)

            # Decrypt file
            chunk_stream = aead_decrypt_chacha(file=f, key=key, iv=first_nonce)

            # Save decrypted file
            with outfile.open(mode='ab+') as outf:

                # Decompress if DS compressed, otherwise save chunks
                func = decompress_file if file_info['compressed'] \
                    else file_writer
                saved, error = func(filehandler=outf,
                                    gen=chunk_stream,
                                    last_nonce=last_nonce)

                if not saved:
                    return False, outfile, error

    except exceptions_ds.DeliverySystemException as dse:
        error = f"Finalizing of file failed! {dse}"
        LOG.exception(error)
        return False, outfile, error
    else:
        LOG.info("File: '%s' -- Finalizing completed! Decrypted file "
                 "saved at '%s'", file, outfile)
    finally:
        os.umask(original_umask)    # Remove mask

    # FINISHED ----------------------------------------------------- FINISHED #

    return True, outfile, ""
