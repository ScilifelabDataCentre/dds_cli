# CHECK CALLING FUNCTION
cur_com = sys._getframe().f_code.co_name  # The current command, "put" here
# The calling function ("invoke" in this case)
cal_com = sys._getframe().f_back.f_code.co_name


# ENCRYPTION KEY CLASS
class ECDHKeyPair:
    """Public key pair.
    Algorithm: Eliptic Curve Diffie-Hellman (Curve25519)"""

    def __init__(self, privatekey: str = "key", publickey: str = "key", temp_dir: str = ""):
        """Generates a public key pair"""

        cb = partial(get_passphrase)    # Get passphrase for private key enc

        # Directory for storing keys
        key_dir = f"{temp_dir}/keys"

        # Paths to private and public keys
        priv_keyname = f"{key_dir}/{privatekey}.sec"
        pub_keyname = f"{key_dir}/{publickey}.pub"

        try:
            # Generate public key pair, encrypt private key
            keys.c4gh.generate(seckey=priv_keyname,
                               pubkey=pub_keyname, callback=cb)
        except EncryptionError as ee:
            self.pub = f"The key pair {priv_keyname}/{pub_keyname} could not be generated: {ee}"
            self.sec = None
        else:
            try:
                # Import keys, decrypt private key
                self.pub = keys.get_public_key(filepath=pub_keyname)
                self.sec = keys.get_private_key(filepath=priv_keyname,
                                                callback=cb)
            except EncryptionError as ee:
                sys.exit(
                    f"Could not get the keys {priv_keyname} & {pub_keyname}: ", f"{ee}")

    def encrypt(self, file: str, remote_pubkey, temp_dir: str, sub_dir: str):
        """Uses the remote public key and the own private key to encrypt a file"""

        error = ""

        fname = file.split('/')[-1]
        if sub_dir == "":
            encrypted_file = f"{temp_dir}/{fname}.c4gh"
        else:
            encrypted_file = f"{sub_dir}/{fname}.c4gh"

        try:
            # Encrypt file
            with open(file=file, mode='rb') as infile:
                with open(file=encrypted_file, mode='wb+') as outfile:
                    # The 0 in keys is the method (only one allowed)
                    lib.encrypt(keys=[(0, self.sec, remote_pubkey)],
                                infile=infile, outfile=outfile)
        except EncryptionError as ee:
            logging.error("Some error message here.")
            error = f"Could not encrypt file {file}: {ee}"
        else:
            logging.info("Some success message here.")

        return encrypted_file, "crypt4gh", error


# CREATE HEADER FOR CRYPT4GH FORMAT BEFORE CHUNK ENCRYPTION
def generate_header(own_private_key, remote_public_key):
    """Generates crypt4gh format header"""

    encryption_method = 0           # ChaCha20
    session_key = os.urandom(32)    # Key (file)
    print(session_key)
    cipher = ChaCha20Poly1305(session_key)  # Cipher (file)

    # 'keys' format: (method, own-private-key, remote-public-key)
    keys = [(0, own_private_key, remote_public_key)]

    header_content = header.make_packet_data_enc(encryption_method=encryption_method,
                                                 session_key=session_key)
    header_packets = header.encrypt(packet=header_content,
                                    keys=keys)
    header_bytes = header.serialize(packets=header_packets)

    return header_bytes, cipher


# CHUNK ENCRYPTION
def _encrypt_segment(data, process, cipher):
    """Utility function to generate a nonce, 
    encrypt data with Chacha20, 
    and authenticate it with Poly1305."""

    try:
        nonce = os.urandom(12)
        encrypted_data = cipher.encrypt(nonce, data, None)  # No add
        # after producing the segment, so we don't start outputing when an error occurs
        process(nonce)
        process(encrypted_data)
        yield encrypted_data
    except EncryptionError as ee:
        yield "error", f"Encryption of chunk failed: {ee}"


# CHUNK DECRYPTION
def try_decryption(encrypted_file: str, keypair: tuple):
    """Tests decryption of encrypted c4gh file"""

    # Deconstruct header
    # body decrypt
    with open(encrypted_file, 'rb') as ef:
        with open(f"{encrypted_file}.decrypted", 'wb') as df:
            lib.decrypt(keys=[(0, keypair[0], keypair[1])], infile=ef,
                        outfile=df, sender_pubkey=keypair[1], offset=0, span=65536)

    # NOT WORKING #
    hash_decrypted = hmac.HMAC(key=key, algorithm=hashes.SHA256(),
                               backend=default_backend())
    hash_decrypted = gen_hmac(filepath=f"{encrypted_file}.decrypted",
                              chunk_size=65536, hash_=hash_decrypted)

    return hash_decrypted


# CHUNK COMPRESSION 
def compress_chunk(original_chunk):
    """Compress individual chunks read in a streamed fashion"""

    try:
        yield gzip.compress(data=original_chunk)
    except CompressionError as ce:
        yield "error", f"Compression of chunk failed: {ce}"


# CHUNK DECOMPRESSION
def decompress_chunk(compressed_chunk):
    """Performs gzip compression and streams compressed chunk"""

    yield gzip.decompress(compressed_chunk)
	

# COMPRESSION -- PROCESS_FILE
hash_original = ""                      # Original file hash
    hash_compressed = ""                    # Compressed file hash
    hash_encrypted = ""                     # Encrypted file hash

    key = b"Thisisakeythatshouldbechanged"
    h_orig = hmac.HMAC(key, hashes.SHA256(), backend=default_backend())
    h_comp = hmac.HMAC(key, hashes.SHA256(), backend=default_backend())

with open(file, 'rb') as f:
        print("Name: ", f.name)
        chunk_stream = stream_chunks(file_handle=f, chunk_size=65536)
        for chunk in chunk_stream:  # Continues here before above is finished
            if isinstance(chunk, tuple):
                logging.error("Some error message here.")
                return {"FAILED": {"Path": f.name,
                                   "Error": chunk[1]}}

            h_orig.update(chunk)    # Update hash for original file

            # If the file is not compressed, compress chunks
            if not is_compressed:
                comp_chunk_stream = compress_chunk(original_chunk=chunk)
                with open(file=f"{file}.gzip", mode='wb') as cf:
                    for comp_chunk in comp_chunk_stream:    # Continues here before above is finished
                        if isinstance(comp_chunk, tuple):
                            logging.error("Some error message here.")
                            return {"FAILED": {"Path": cf.name,
                                               "Error": comp_chunk[1]}}

                        # Updates hash for compressed file
                        h_comp.update(comp_chunk)

                        # Save compressed chunk to file
                        cf.write(comp_chunk)

                    is_compressed = True
                    compression_algorithm = "gzip"
                    latest_path = cf.name

            else:
                latest_path = file

    hash_original = h_orig.finalize().hex()
    hash_compressed = h_comp.finalize().hex()


# IF NOT SENSITIVE - NOT RELEVANT -- PROCESS_FILE
else:   # If not sensitive
	if is_compressed:   # If compressed
		# TODO: hash
		hash_compressed = gen_hmac(
			filepath=file, chunk_size=65536, hash_=hash_compressed)
	else:   # If NOT compressed
		# TODO: hash + compress + hash
		comp_dir = new_dir(filename=fname,
							sub_dir=sub_dir,
							temp_dir=temp_dir,
							operation="compression")
		hash_original, hash_compressed, \
			latest_path = hash_compress_hash_encrypt_hash(file=file,
															compressed_file=comp_dir,
															hash_original=hash_original,
															hash_compressed=hash_compressed)


# FILE PROCESSING -- ENCRYPTION ETC - PROCESS_FILE
if sensitive:
        # Generate keys
        researcher_kp = ECDHKeyPair(privatekey=f"{fname}_researcher",
                                    publickey=f"{fname}_researcher",
                                    temp_dir=temp_dir)
        facility_kp = ECDHKeyPair(privatekey=f"{fname}_facility",
                                  publickey=f"{fname}_facility",
                                  temp_dir=temp_dir)
        if researcher_kp.sec is None:
            logging.error("Some error message here.")
            return {"FAILED": {"Path": latest_path,
                               "Error": researcher_kp.pub}}
        elif facility_kp.sec is None:
            logging.error("Some error message here.")
            return {"FAILED": {"Path": latest_path,
                               "Error": facility_kp.pub}}

        if is_compressed:   # If file is compressed
            # TODO: hash + encrypt + hash
            enc_dir = new_dir(filename=fname,
                              sub_dir=sub_dir,
                              temp_dir=temp_dir,
                              operation="encryption")
            hash_compressed, hash_encrypted, \
                latest_path = hash_encrypt_hash(file=file,
                                                encrypted_file=enc_dir,
                                                keypair=(facility_kp.sec,
                                                         researcher_kp.pub),
                                                hash_compressed=hash_compressed,
                                                hash_encrypted=hash_encrypted)
        else:   # If file is NOT compressed
            # TODO: hash + compress + hash + encrypt + hash
            comp_dir = new_dir(filename=fname,
                               sub_dir=sub_dir,
                               temp_dir=temp_dir,
                               operation="compression")
            enc_dir = new_dir(filename=comp_dir.split("/")[-1],
                              sub_dir=sub_dir,
                              temp_dir=temp_dir,
                              operation="encryption")

            hash_original, hash_compressed, \
                hash_encrypted, latest_path = hash_compress_hash_encrypt_hash(file=file,
                                                                              encrypted_file=enc_dir,
                                                                              keypair=(facility_kp.sec,
                                                                                       researcher_kp.pub),
                                                                              hash_original=hash_original,
                                                                              hash_compressed=hash_compressed,
                                                                              hash_encrypted=hash_encrypted)

            hash_decrypted = try_decryption(
                encrypted_file=latest_path, keypair=(researcher_kp.sec, facility_kp.pub))
            print(hash_decrypted, hash_original,
                  hash_decrypted == hash_original)


# CHECKSUM GENERATION
def gen_hmac(filepath: str, chunk_size: int, hash_) -> str:
    """Generates HMAC for file"""

    try:
        with open(filepath, 'rb') as f:
            for compressed_chunk in iter(lambda: f.read(chunk_size), b''):
                hash_.update(compressed_chunk)
    except HashException as he:
        logging.error("Some error message here.")
        error = f"Checksum generation for file {filepath} failed. Can not guarantee file integrity. "
    else:
        logging.info("Some success message here.")

    return hash_.finalize().hex()

    # key = b"ina"
    # h = hmac.HMAC(key, hashes.SHA256(), backend=default_backend())

    # with open(filepath, 'rb') as f:
    #     for chunk in iter(lambda: f.read(16384), b''):
    #        h.update(chunk)

    # return h.finalize().hex(), error


# PROCESSING IN DIFFERENT ORDERS
def hash_compress_hash(file: str, compressed_file: str,
                       hash_original, hash_compressed) -> (str, str, str):
    """hash + compress + hash"""

    with open(file=file, mode='rb') as of:
        with open(file=compressed_file, mode='wb') as cf:
            chunk_stream = stream_chunks(file_handle=of, chunk_size=65536)
            for chunk in chunk_stream:
                hash_original.update(chunk)

                compressed_stream = compress_chunk(original_chunk=chunk)
                for compressed_chunk in compressed_stream:
                    hash_compressed.update(compressed_chunk)

                    cf.write(compressed_chunk)

    return hash_original.finalize().hex(), hash_compressed.finalize().hex(), \
        compressed_file


def hash_compress_hash_encrypt_hash(file: str, encrypted_file: str, keypair,
                                    hash_original, hash_compressed, hash_encrypted) -> (str, str, str, str):
    """hash + compress + hash + encrypt + hash"""

    header_bytes, cipher = generate_header(keypair[0], keypair[1])

    with open(file=file, mode='rb') as of:
        with open(file=encrypted_file, mode='wb') as ef:
            ef.write(header_bytes)
            chunk_stream = stream_chunks(file_handle=of, chunk_size=65536)
            for chunk in chunk_stream:
                hash_original.update(chunk)

                compressed_stream = compress_chunk(original_chunk=chunk)
                for compressed_chunk in compressed_stream:
                    hash_compressed.update(compressed_chunk)

                    encrypted_stream = _encrypt_segment(data=compressed_chunk,
                                                        process=ef.write,
                                                        cipher=cipher)
                    for encrypted_chunk in encrypted_stream:
                        hash_encrypted.update(encrypted_chunk)

    return hash_original.finalize().hex(), hash_compressed.finalize().hex(), \
        hash_encrypted.finalize().hex(), encrypted_file


def hash_encrypt_hash(file: str, encrypted_file: str, keypair,
                      hash_compressed, hash_encrypted) -> (str, str, str):
    """hash + encrypt + hash"""

    header_bytes, cipher = generate_header(keypair[0], keypair[1])

    with open(file=file, mode='rb') as cf:
        with open(file=encrypted_file, mode='wb') as ef:
            ef.write(header_bytes)
            chunk_stream = stream_chunks(file_handle=cf, chunk_size=65536)
            for compressed_chunk in chunk_stream:
                hash_compressed.update(compressed_chunk)
                encrypted_stream = _encrypt_segment(data=compressed_chunk,
                                                    process=ef.write,
                                                    cipher=cipher)
                for encrypted_chunk in encrypted_stream:
                    hash_encrypted.update(encrypted_chunk)

    return hash_compressed.finalize().hex(), \
        hash_encrypted.finalize().hex(), file


def hash_dir(dir_path: str, key) -> str:
    """Generates a hash for all contents within a folder"""

    # Initialize HMAC
    dir_hmac = hmac.HMAC(key, hashes.SHA256(), backend=default_backend())

    # Recursively walk through the folder
    for path, dirs, files in os.walk(dir_path):
        for file in sorted(files):  # For all files in folder root
            # Generate file hash and update directory hash
            dir_hmac.update(gen_hmac(os.path.join(path, file)))
        for dir_ in sorted(dirs):   # For all folders in folder root
            # Walk through child folder
            hash_dir(os.path.join(path, dir_), key)
        break

    return dir_hmac.finalize().hex()


# DATABASE STUFF -- COUCH DISCONNECTION
def couch_disconnect(couch, token):
    """Disconnect from couchdb interface."""

    try:
        couch.logout(token)
    except CouchDBException:
        print("Could not logout from database.")


# DELIVERY PORTAL ACCESS -- BASICALLY SAME THING AS IN CODE CHECK_ACCESS 
def dp_access(username: str, password: str, upload: bool) -> (bool, str):
    """Check existance of user in database and the password validity."""

    try:
        user_db = couch_connect()['user_db']    # Connect to user database
    except CouchDBException as cdbe:
        sys.exit(f"Could not collect database 'user_db'. {cdbe}")
    else:
        # Search the database for the user
        for id_ in user_db:
            # If the username does not exist in the database quit
            if username != user_db[id_]['username']:
                raise CouchDBException("Invalid username, "
                                       "user does not exist in database. ")
            else:
                # If the password isn't correct quit
                if user_db[id_]['password']['hash'] != secure_password_hash(password_correct=user_db[id_]['password'],
                                                                            password_entered=password):
                    raise DeliveryPortalException("Wrong password. "
                                                  "Access to Delivery Portal "
                                                  "denied.")
                else:
                    # If facility is uploading or researcher is downloading
                    # access is granted
                    if (user_db[id_]['role'] == 'facility' and upload) or \
                            (user_db[id_]['role'] == 'researcher' and not upload):
                        return True, id_
                    else:
                        if upload:
                            option = "Upload"
                        else:
                            option = "Download"
                        raise DeliveryOptionException("Chosen upload/download "
                                                      "option not granted. "
                                                      f"You chose: '{option}'. "
                                                      "For help: 'dp_api --help'")


# VALIDATE API OPTIONS - ALREADY IN CODE
def validate_api_options(config: str, username: str, password: str, project: str,
                         pathfile: str, data: tuple) -> (str, str, str):
    """Checks if all required options are entered etc."""

    # All credentials entered? Exception raised if not.
    username, password, project = verify_user_credentials(config=config,
                                                          username=username,
                                                          password=password,
                                                          project=project)

    # Data to be uploaded entered? Exception raised if not.
    if not data and not pathfile:
        raise DeliveryPortalException(
            "No data to be uploaded. Specify individual files/folders using "
            "the --data/-d option one or more times, or the --pathfile/-f. "
            "For help: 'dp_api --help'"
        )

    return username, password, project
	

# GET FILESIZE
def get_filesize(filename: str) -> (int):
    """Returns file size"""

    return os.stat(filename).st_size


# GET PASSSPHRASE 
def get_passphrase():
    """Gets passphrase for private key encryption"""

    return "thisisapassphrasethatshouldbegeneratedsomehow"


# UNCLEAR 
def new_dir(filename: str, sub_dir: str, temp_dir: str, operation: str) -> (str):
"""Checks which dir to place file in"""

ext = ""
if operation == "compression":
	ext = ".gzip"
elif operation == "encryption":
	ext = ".c4gh"
else:
	pass    # Non allowed operation

if sub_dir == "":
	return f"{temp_dir}/{filename}{ext}"
else:
	return f"{sub_dir}/{filename}{ext}"


# CHECKS IF NGS TYPE - ALREADY IN CODE
def ngs_type(extension: str):
    """Checks if the file is of ngs type"""

    mime = ""
    if extension == "": 
        mime = None
    elif extension in (".abi", ".ab1"):
        mime = "ngs-data/abi"
    elif extension in (".embl"):
        mime = "ngs-data/embl"
    elif extension in (".clust", ".cw", ".clustal"):
        mime = "ngs-data/clustal"
    elif extension in (".fa", ".fasta", ".fas", ".fna", ".faa", ".afasta"):
        mime = "ngs-data/fasta"
    elif extension in (".fastq", ".fq"):
        mime = "ngs-data/fastq"
    elif extension in (".gbk", ".genbank", ".gb"):
        mime = "ngs-data/genbank"
    elif extension in (".paup", ".nexus"):
        mime = "ngs-data/nexus"
    else:
        mime = None

    return mime


# STREAM CHUNKS 
def stream_chunks(file_handle, chunk_size):
    """Reads file and returns (streams) the content in chunks"""

    try:
        for chunk in iter(lambda: file_handle.read(chunk_size), b''):
            yield chunk
    except StreamingError as se:
        yield "error", f"Could not yield chunk: {se}"