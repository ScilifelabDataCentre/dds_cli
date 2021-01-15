"""File handler module.

Responsible for IO related operations, including compression, encryption, etc.
Also contains the variables MAGIC_DICT (all checked compression formats) and
MAX_NONCE (the maximum number of nonces allowed for the same key).
"""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import logging
import os
import pathlib

# Installed
from nacl.bindings import crypto_aead_chacha20poly1305_ietf_decrypt as decrypt
from nacl.bindings import crypto_aead_chacha20poly1305_ietf_encrypt as encrypt
import zstandard as zstd

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
# TODO (ina): Add xz and 7z
MAGIC_DICT = {
    b"\x913HF": "hap",
    b"`\xea": "arj",
    b"_\'\xa8\x89": "jar",
    b"ZOO ": "zoo",
    b"PK\x03\x04": "zip",
    b"\x1F\x8B": "gzip",
    b"UFA\xc6\xd2\xc1": "ufa",
    b"StuffIt ": "sit",
    b"Rar!\x1a\x07\x00": "rar v4.x",
    b"Rar!\x1a\x07\x01\x00": "rar v5",
    b"MAr0\x00": "mar",
    b"DMS!": "dms",
    b"CRUSH v": "cru",
    b"BZh": "bz2",
    b"-lh": "lha",
    b"(This fi": "hqx",
    b"!\x12": "ain",
    b"\x1a\x0b": "pak",
    b"(\xb5/\xfd": "zst"
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
    """Delete file

    Args:
        file (Path):    Path to file

    """

    if not file.exists():
        return False, f"File does not exist: {file}"

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
    """Yields the file chunk by chunk.

    Args:
        file:           Path to file
        chunk_size:     Number of bytes to read from file at a time

    Yields:
        bytes:  Data chunk of size chunk_size
    """

    for chunk in iter(lambda: filehandler.read(chunk_size), b""):
        yield chunk


# NOTE: Merge this with decompress_file?
def file_writer(filehandler, gen, last_nonce):
    """Writes decrypted chunks to file. Checks if last nonces match.

    Args:
        filehandler:            Filehandler to save decompressed chunks to/with
        gen:                    Generator - all decrypted chunks streamed
        last_nonce (bytes):     Last nonce found from file

    Returns:
        tuple:  Info on saved file, decryption and decompression

            bool:   True if file saved and last nonce is correct
            str:    Error message, "" if none

    """

    nonce = b""  # Catches last nonce while decompressing decrypted chunk

    # Save chunks to file
    for nonce, chunk in gen:
        filehandler.write(chunk)

    # If reached end of file but nonces don't match - the entire file has not
    # been delivered -- error
    nonce_ok, error = check_last_nonce(filename=filehandler.name,
                                       last_nonce=last_nonce,
                                       nonce=nonce)

    return nonce_ok, error


def get_dir_info(folder: pathlib.Path, do_fail: bool) -> (dict, dict):
    """Iterate through folder contents and get file info

    Args:
        folder (Path):  Path to folder

    Returns:
        dict:   Files to deliver
        dict:   Files which failed -- not to deliver
    """

    # Variables ############################ Variables #
    dir_info = {}   # Files to deliver
    dir_fail = {}   # Failed files
    # -------------------------------------------------#

    # Iterate through folder contents and get file info
    for f in folder.glob("**/*"):
        if f.is_file() and "DS_Store" not in str(f):    # CHANGE LATER
            file_info = get_file_info(file=f,
                                      in_dir=True,
                                      do_fail=do_fail,
                                      dir_name=folder)

            # If file check failed in some way - do not deliver file
            # Otherwise deliver file -- no cancellation of folder here
            if not file_info["proceed"]:
                dir_fail[f] = file_info
            else:
                dir_info[f] = file_info

    return dir_info, dir_fail


def get_file_info_rec(path: pathlib.Path, do_fail: bool, root: bool = True,
                      folder: pathlib.Path = None):
    """Docstring"""
    # TODO (Ina): Add docstring

    proceed = True  # If proceed with file delivery

    # Error if single file specified but a folder passed as arg
    if (not root and folder is None) or (root and folder is not None):
        LOG.critical("Error message here!")

    print("\nPath: ", path, " - Root: ", root)
    final_dict = {}

    if path.is_dir():
        for f in path.glob("**/*"):
            if f.is_file() and "DS_Store" not in str(f):
                final_dict.update(
                    get_file_info_rec(path=f, do_fail=do_fail, root=False,
                                      folder=path.name)
                )
        print("Folder: ", path.name)
    else:
        # TODO (ina): Change names of the dict keys - more logical
        final_dict = {path: {
            "in_directory": not root,  # single file entered or in folder
            "local_dir_path": folder,  # local directory, specified in cli call
            # sub directory from spec fold
            "directory_path": get_subdir(file=path, folder=folder)
        }}

        # Check if file is compressed and fail delivery on error
        compressed, error = is_compressed(file=path)
        error = "fail"
        if error != "":
            return {path: {**final_dict[path], **{"proceed": False, "error": error}}}

        suff_aftproc = ""  # Suffixes after processing
        # If file not compressed -- add zst (Zstandard) suffix to final suffix
        # If compressed -- info that DS will not compress
        if not compressed:
            # Warning if suffixes are in magic dict but file "not compressed"
            if set(path.suffixes).intersection(set(MAGIC_DICT)):
                LOG.warning("File '%s' has extensions belonging "
                            "to a compressed format but shows no "
                            "indication of being compressed. Not "
                            "compressing file.", path)

            suff_aftproc += ".zst"     # Update the future suffix
        elif compressed:
            LOG.info("File '%s' shows indication of being "
                     "in a compressed format. "
                     "Not compressing the file.", path)

        # Add (own) encryption format extension
        suff_aftproc += ".ccp"     # ChaCha20-Poly1305

        # Path to file in temporary directory after processing, and bucket
        # after upload, >>including file name<<
        path_in_db = final_dict[path]["directory_path"] / \
            pathlib.Path(path.name)
        path_in_bucket = path_in_db.with_suffix(
            "".join(path.suffixes) + suff_aftproc)
        final_dict[path].update({
            "size": path.stat().st_size,
            "proceed": proceed,
            "compressed": compressed,
            "path_in_bucket": str(path_in_bucket),
            "path_in_db": str(path_in_db),  # "local path"?
            "error": error,
            "encrypted_file": pathlib.Path(""),
            "encrypted_size": 0,
            "key": "",  # public key (?)
            "extension": suff_aftproc,  # suffixes after processing
            "processing": {"in_progress": False,
                           "finished": False},
            "upload": {"in_progress": False,
                        "finished": False},
            "database": {"in_progress": False,
                         "finished": False}
        })

    return final_dict


def get_file_info(file: pathlib.Path, in_dir: bool, do_fail: bool,
                  dir_name: pathlib.Path = pathlib.Path("")) -> (dict):
    """Get info on file and check if already delivered

    Args:
        file (Path):        Path to file
        in_dir (bool):      True if in directory specified by user
        dir_name (Path):    Directory name, "" if not in folder

    Returns:
        dict:   Information about file e.g. format

    """

    # Variables ###################################### Variables #
    proceed = True  # If proceed with file delivery

    # Folder name and path to file IN folder
    path_base = dir_name.name if in_dir else None
    directory_path = get_subdir(file=file, folder=path_base) \
        if path_base is not None else pathlib.Path("")
    print("Directory path: ", directory_path)
    print("Current working directory: ", os.getcwd())
    dir_info = {"in_directory": in_dir, "local_dir_name": dir_name}

    suffixes = file.suffixes    # File suffixes
    proc_suff = ""              # Saves final suffixes
    error = ""                  # Error message
    # ---------------------------------------------------------- #

    # Cancel if delivery tagged as failed
    if do_fail:
        error = "Break on fail specified and one fail occurred. " + \
                "Cancelling delivery."
        LOG.info(error)
        return {"proceed": False, "error": error, **dir_info}

    # Check if file is compressed and fail delivery on error
    compressed, error = is_compressed(file=file)
    if error != "":
        return {"proceed": False, "error": error, **dir_info}

    # If file not compressed -- add zst (Zstandard) suffix to final suffix
    # If compressed -- info that DS will not compress
    if not compressed:
        # Warning if suffixes are in magic dict but file "not compressed"
        if set(suffixes).intersection(set(MAGIC_DICT)):
            LOG.warning("File '%s' has extensions belonging "
                        "to a compressed format but shows no "
                        "indication of being compressed. Not "
                        "compressing file.", file)

        proc_suff += ".zst"     # Update the future suffix
    elif compressed:
        LOG.info("File '%s' shows indication of being "
                 "in a compressed format. "
                 "Not compressing the file.", file)

    # Add (own) encryption format extension
    proc_suff += ".ccp"     # ChaCha20-Poly1305

    # Path to file in temporary directory after processing, and bucket
    # after upload, >>including file name<<
    path_in_db = directory_path / pathlib.Path(file.name)
    path_in_bucket = path_in_db.with_suffix("".join(suffixes) + proc_suff)
    return {"in_directory": in_dir,
            "local_dir_name": dir_name if in_dir else None,
            "directory_path": directory_path,
            "size": file.stat().st_size,
            "proceed": proceed,
            "compressed": compressed,
            "path_in_bucket": str(path_in_bucket),
            "path_in_db": str(path_in_db),
            "error": error,
            "encrypted_file": pathlib.Path(""),
            "encrypted_size": 0,
            "key": "",
            "extension": proc_suff,
            "processing": {"in_progress": False,
                           "finished": False},
            "upload": {"in_progress": False,
                       "finished": False},
            "database": {"in_progress": False,
                         "finished": False}}


def get_subdir(file: pathlib.Path, folder: str = None) -> (pathlib.Path):
    """Gets the path to the file, from the entered folder.

    Args:
        file:       Path to file
        path_base:  None if single file, folder name if in folder

    Returns:
        Path:   Path from folder to file
    """

    subdir = pathlib.Path("")

    if folder is not None:
        fileparts = file.parts
        start_ind = fileparts.index(folder)
        subdir = pathlib.Path(*fileparts[start_ind:-1])

    return subdir


###############################################################################
# COMPRESSION ################################################### COMPRESSION #
###############################################################################
# NOTE: Move to own module/class?


def compress_file(filehandler, chunk_size: int = SEGMENT_SIZE) -> (bytes):
    """Compresses file by reading it chunk by chunk.

    Args:
        file:           Path to file
        chunk_size:     Number of bytes to compress at a time

    Yields:
        bytes:  Compressed data chunk

    """

    # Initiate a Zstandard compressor
    cctzx = zstd.ZstdCompressor(write_checksum=True, level=4)

    # Compress file chunk by chunk while reading
    with cctzx.stream_reader(filehandler) as compressor:
        for chunk in iter(lambda: compressor.read(chunk_size), b""):
            yield chunk


# TODO(ina): Merge this with file_writer?
def decompress_file(filehandler, gen, last_nonce: bytes) -> (bool, str):
    """Decompresses file

    Args:
        filehandler:            Filehandler to save decompressed chunks to/with
        gen:                    Generator - all decrypted chunks streamed
        last_nonce (bytes):     Last nonce found from file

    Returns:
        tuple:  Info on saved file, decryption and decompression

            bool:   True if file saved and last nonce is correct
            str:    Error message, "" if none

    """

    nonce = b""     # Catches last nonce while decompressing decrypted chunk

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
    """Checks for file signatures in common compression formats.

    Args:
        file (Path):   Path object to be checked.

    Returns:
        tuple:      Info on if compressed format or not.

            bool:   True if file is compressed format.
            str:    Error message, "" if no error
    """

    error = ""  # Error message

    try:
        # Check for file signature in beginning of file
        with file.open(mode="rb") as f:
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
    """Decrypts the file in chunks.

    Decrypts the file in chunks using the IETF ratified ChaCha20-Poly1305
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

    """

    # NOTE: Fix return error here?
    # If position not directly after first nonce, then error - fail
    if file.tell() != 12:
        raise exceptions_ds.DeliverySystemException(
            f"Reading encrypted file {file.name} failed!")

    # Variables ################################################### Variables #
    iv_int = int.from_bytes(iv, "little")           # Transform nonce to int
    aad = None              # Associated data, unencrypted but authenticated
    # ----------------------------------------------------------------------- #

    for enc_chunk in iter(lambda: file.read(CIPHER_SEGMENT_SIZE), b""):
        # Get nonce as bytes for decryption: if the nonce is larger than the
        # max number of chunks allowed to be encrypted (safely) -- begin at 0
        nonce = (iv_int if iv_int < MAX_NONCE
                 else iv_int % MAX_NONCE).to_bytes(length=12,
                                                   byteorder="little")

        iv_int += 1  # Increment nonce

        # Decrypt and yield nonce and plaintext
        yield (nonce, decrypt(ciphertext=enc_chunk,
                              aad=aad,
                              nonce=nonce,
                              key=key))


def aead_encrypt_chacha(gen, key: bytes, iv: bytes) -> (bytes, bytes):
    """Encrypts the file in chunks.

    Encrypts the file in chunks using the IETF ratified ChaCha20-Poly1305
    construction described in RFC7539.

    Args:
        gen (Generator):    Generator object, stream of file chunks
        key (bytes):        Data encryption key
        iv (bytes):         Initial nonce

    Yields:
        tuple:  The nonce for each data chunk and ciphertext

            bytes:  Nonce -- number only used once
            bytes:  Ciphertext
    """
    # TODO (ina): Move this to crypto module?

    # Variables ################################################### Variables #
    iv_int = int.from_bytes(iv, "little")   # Transform nonce to int
    aad = None  # Associated data, unencrypted but authenticated
    # ----------------------------------------------------------------------- #

    for chunk in gen:
        # Get nonce as bytes for encryption: if the nonce is larger than the
        # max number of chunks allowed to be encrypted (safely) -- begin at 0
        nonce = (iv_int if iv_int < MAX_NONCE
                 else iv_int % MAX_NONCE).to_bytes(length=12,
                                                   byteorder="little")
        # LOG.debug(f"\nnonce in encryption: \t{nonce}\n")

        iv_int += 1  # Increment nonce

        # Encrypt and yield nonce and ciphertext
        yield nonce, encrypt(message=chunk,
                             aad=aad,
                             nonce=nonce,
                             key=key)


def check_last_nonce(filename: str, last_nonce: bytes, nonce: bytes) \
        -> (bool, str):
    """Check if the nonces match and give error if they don't.

    Args:
        filename (str):     File name
        last_nonce (bytes):     Last nonce (read from end of encrypted file)
        nonce (bytes):          Nonce which decryption/decompression ended on

    Returns:
        tuple:  Info on delivery ok or not

            bool:   True if the nonces match
            str:    Error message, "" if none

    """

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
    """Processes the files before upload.

    Compresses the files that are not already in a compressed format,
    encrypts them using the algorithm ChaCha20-Poly1305 and returns info about
    what processing has been performed and the public key component. The secret
    key is not saved since the uploader should not be able to decrypt.

    Args:
        file (Path):           Path to file
        file_info (dict):      Info about file

    Returns:
        tuple: Information about finished processing
            bool:   True if processing successful\n
            Path:   Path to processed file\n
            int:    Size of processed file\n
            bool:   True if file compressed by the delivery system\n
            bytes:  Public key needed for file decryption\n
            bytes:  Salt needed for shared key derivation\n
            str:    Error message, '' if none\n

    Raises:
        DeliverySystemException:    Failed processing or wrong argument format
        OSError:                    File not found or could not create tempdir
    """
    # TODO (ina): Look into using signing etc for the keys.
    # If file path not Path type --> quit whole execution, something wrong
    if not isinstance(file, pathlib.Path):
        emessage = f"Wrong format! {file} is not a 'Path' object."
        raise exceptions_ds.DeliverySystemException(emessage)

    # If file doesn't exist --> quit whole execution, something wrong
    if not file.exists():
        emessage = f"The path {file} does not exist!"
        raise OSError(emessage)  # Bug somewhere in code

    # Variables ################################################### Variables #
    outfile = DIRS[1] / file_info["path_in_bucket"]   # Path to save processed
    new_dir = DIRS[1] / file_info["directory_path"]     # New temp subdir
    key = b""
    # ----------------------------------------------------------------------- #
    LOG.debug("Infile: '%s', Outfile: '%s'", file, outfile)

    # Encryption key ######################################### Encryption key #
    keypair = crypto_ds.ECDHKey()    # Create new ECDH key pair

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
        with file.open(mode="rb") as f:

            # Check if to compress or read
            func = file_reader if file_info["compressed"] else compress_file

            # Compression ###### If not already compressed ###### Compression #
            chunk_stream = func(filehandler=f)

            # Encryption ######################################### Encryption #
            with outfile.open(mode="wb+") as outf:
                # Generate initial nonce and save to file
                iv_bytes = os.urandom(12)
                outf.write(iv_bytes)
                LOG.debug("File: '%s' IV: %s", file, iv_bytes)

                # Encrypt and save ciphertext (not nonces) to file
                nonce = b""     # Catches the nonces
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
        # print("\n\n\n\n", file_info["compressed"],
        #       type(file_info["compressed"]),
        #       "\n\n\n\n")
        ds_compressed = not file_info["compressed"]
    finally:
        os.umask(original_umask)    # Remove mask

    # PROCESSING FINISHED ------------------------------- PROCESSING FINISHED #
    return (True, outfile, outfile.stat().st_size, ds_compressed,
            keypair.public_to_hex(), salt.hex().upper(), "")


def reverse_processing(file: str, file_info: dict, keys: tuple) \
        -> (bool, str, str):
    """Decrypts and decompresses file (if DS compressed)

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

    """

    # Variables ################################################### Variables #
    infile = file_info["path_in_temp"]                      # Downloaded file
    outfile = DIRS[1] / pathlib.Path(file)   # Finalized file path
    error = ""
    # ----------------------------------------------------------------------- #
    LOG.debug("Infile: %s, Outfile: %s", infile, outfile)

    # Encryption key ######################################### Encryption key #
    # Get keys for decryption
    peer_public = bytes.fromhex(file_info["public_key"])  # File public enc key
    keypair = crypto_ds.ECDHKey(keys=keys)          # Project specific key pair
    LOG.debug("public key peer: %s\npublic key peer: %s",
              peer_public, peer_public.hex().upper())

    # Derive shared symmetric key
    salt = file_info["salt"]                # Salt to generate same shared key
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
        with infile.open(mode="rb+") as f:
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
            with outfile.open(mode="ab+") as outf:

                # Decompress if DS compressed, otherwise save chunks
                func = decompress_file if file_info["compressed"] \
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
