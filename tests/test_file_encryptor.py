import hashlib
import pathlib
import typing
from dds_cli import file_encryptor
from dds_cli import FileSegment
from dds_cli import file_handler_local
from pyfakefs.fake_filesystem import FakeFilesystem
import os
import csv
from cryptography.hazmat.primitives import asymmetric, serialization
from cryptography.hazmat.primitives.asymmetric import x25519

# Encryptor.__init__ / Decryptor.__init__


def key_pair():
    """Generate a Curve 25519 key pair."""
    private_key = asymmetric.x25519.X25519PrivateKey.generate()
    private_key_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_key_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return private_key_bytes.hex().upper(), public_key_bytes.hex().upper()


def test_encryptor():
    """Generate encryption key."""
    # Generate key pairs
    project_private_key, project_public_key = key_pair()

    # Generate encryption key
    encryptor = file_encryptor.Encryptor(project_keys=[project_private_key, project_public_key])
    assert isinstance(encryptor.peer_public, x25519.X25519PublicKey)
    assert isinstance(encryptor.my_private, x25519.X25519PrivateKey)
    assert isinstance(encryptor.key, bytes)
    assert isinstance(encryptor.salt, str)


def test_decryptor():
    """Generate decryption key"""
    # Generate key pairs
    project_private_key, project_public_key = key_pair()
    _, file_public_key = key_pair()

    # Generate encryption key
    encryptor = file_encryptor.Encryptor(project_keys=[project_private_key, project_public_key])
    decryptor = file_encryptor.Decryptor(
        project_keys=(project_private_key, project_public_key),
        peer_public=file_public_key,
        key_salt=encryptor.salt,
    )
    assert isinstance(decryptor.peer_public, x25519.X25519PublicKey)
    assert isinstance(decryptor.my_private, x25519.X25519PrivateKey)
    assert isinstance(decryptor.key, bytes)

    # Make sure they're not the same
    assert encryptor.peer_public != decryptor.peer_public
    assert encryptor.my_private != decryptor.my_private


def test_generate_shared_key_ok():
    # Generate key pairs
    project_private_key, project_public_key = key_pair()

    # Generate encryption key
    encryptor = file_encryptor.Encryptor(project_keys=[project_private_key, project_public_key])
    encryptor_public_key = encryptor.public_to_hex(public_key=encryptor.my_private.public_key())

    # Generate decryption key
    decryptor = file_encryptor.Decryptor(
        project_keys=(project_private_key, project_public_key),
        peer_public=encryptor_public_key,
        key_salt=encryptor.salt,
    )
    decryptor_public_key = decryptor.public_to_hex(public_key=decryptor.my_private.public_key())

    # Verify matching public / private
    assert (
        encryptor_public_key
        == decryptor.public_to_hex(public_key=decryptor.peer_public)
        == encryptor.public_to_hex(public_key=decryptor.peer_public)
    )
    assert (
        decryptor_public_key
        == encryptor.public_to_hex(public_key=encryptor.peer_public)
        == decryptor.public_to_hex(public_key=encryptor.peer_public)
    )

    # Verify same key
    assert encryptor.key == decryptor.key


def test_generate_shared_key_not_ok():
    # Generate key pairs
    project_private_key, project_public_key = key_pair()
    _, file_public_key = key_pair()

    # Generate encryption key
    encryptor = file_encryptor.Encryptor(project_keys=[project_private_key, project_public_key])

    # Generate decryption key
    decryptor = file_encryptor.Decryptor(
        project_keys=(project_private_key, project_public_key),
        peer_public=file_public_key,
        key_salt=encryptor.salt,
    )

    # Verify same key
    assert encryptor.key != decryptor.key


# verify_checksum

# - text files


def verify_files_txt(fs: FakeFilesystem, magnitude: str):
    """Perform checksum generation and verification for files of specific sizes."""
    # Specify number of lines to add
    num_lines: int = 0
    if magnitude == "less":
        num_lines = 100
    elif magnitude == "more":
        num_lines = 10000

    # Define lines to input
    line_contents: str = "abcdefghijklmnopqrstuvwxyzåäö"
    lines: typing.List = [line_contents] * num_lines

    # Create fake files and verify that they have same size
    fake_file_path_1: pathlib.Path = pathlib.Path("small_text_file_1.txt")
    fake_file_path_2: pathlib.Path = pathlib.Path("small_text_file_2.txt")
    for file in [fake_file_path_1, fake_file_path_2]:
        fs.create_file(file)
        assert os.path.exists(file)
        with open(file, mode="w") as f:
            f.writelines(lines)
        assert len(line_contents) < os.stat(file).st_size
        if magnitude == "less":
            assert os.stat(file).st_size < FileSegment.SEGMENT_SIZE_RAW
        elif magnitude == "more":
            assert os.stat(file).st_size > FileSegment.SEGMENT_SIZE_RAW
    assert os.stat(fake_file_path_1).st_size == os.stat(fake_file_path_2).st_size

    # Generate checksums
    checksum_file_1 = hashlib.sha256()
    for chunk in file_handler_local.LocalFileHandler.read_file(file=fake_file_path_1):
        checksum_file_1.update(chunk)

    checksum_file_2 = hashlib.sha256()
    for chunk in file_handler_local.LocalFileHandler.read_file(file=fake_file_path_2):
        checksum_file_2.update(chunk)

    # Make sure they are identical
    checksum_hexdigest_1 = checksum_file_1.hexdigest()
    checksum_hexdigest_2 = checksum_file_2.hexdigest()
    assert checksum_hexdigest_1 == checksum_hexdigest_2

    # Make sure verify_checksum gives the same
    fake_1_verified, message1 = file_encryptor.Encryptor.verify_checksum(
        file=fake_file_path_1, correct_checksum=checksum_hexdigest_1
    )
    assert fake_1_verified and message1 == "File integrity verified."
    fake_2_verified, message2 = file_encryptor.Encryptor.verify_checksum(
        file=fake_file_path_2, correct_checksum=checksum_hexdigest_2
    )
    assert fake_2_verified and message2 == "File integrity verified."

    # Change one file slightly
    with open(fake_file_path_1, mode="a") as f:
        f.write("additionaltext")
    assert os.stat(fake_file_path_1).st_size > os.stat(fake_file_path_2).st_size

    # Create new checksum for altered file
    checksum_file_1_altered = hashlib.sha256()
    for chunk in file_handler_local.LocalFileHandler.read_file(file=fake_file_path_1):
        checksum_file_1_altered.update(chunk)

    # Verify that checksum has changed
    checksum_hexdigest_1_altered = checksum_file_1_altered.hexdigest()
    assert checksum_hexdigest_1_altered != checksum_hexdigest_1

    # Verify that verify_checksum fails to verify integrity
    fake_1_altered_verified, message1altered = file_encryptor.Encryptor.verify_checksum(
        file=fake_file_path_1, correct_checksum=checksum_hexdigest_1
    )
    assert (
        not fake_1_altered_verified
        and message1altered
        == "Checksum verification failed. File 'small_text_file_1.txt' compromised."
    )


def test_verify_checksum_less_than_chunk_textfile(fs: FakeFilesystem):
    """Check that the verify_checksum function verifies integrity when size less than 64 KiB."""
    verify_files_txt(fs=fs, magnitude="less")


def test_verify_checksum_more_than_chunk_textfile(fs: FakeFilesystem):
    """Check that the verify_checksum function verifies integrity when size more than 64 KiB."""
    verify_files_txt(fs=fs, magnitude="more")


# - Images


def test_verify_checksum_images():
    """Perform checksum generation and verification for files of specific sizes."""
    image_1a: pathlib.Path = pathlib.Path.cwd() / pathlib.Path("tests/images/test-image_1a.jpg")
    print(image_1a, flush=True)
    image_1b: pathlib.Path = pathlib.Path("tests/images/test-image_1b.jpg")
    image_2: pathlib.Path = pathlib.Path("tests/images/test-image_2.jpg")
    assert image_1a.exists()
    assert image_1b.exists()
    assert image_2.exists()

    # Generate checksums
    checksum_image_1a = hashlib.sha256()
    for chunk in file_handler_local.LocalFileHandler.read_file(file=image_1a):
        checksum_image_1a.update(chunk)

    checksum_image_1b = hashlib.sha256()
    for chunk in file_handler_local.LocalFileHandler.read_file(file=image_1b):
        checksum_image_1b.update(chunk)

    checksum_image_2 = hashlib.sha256()
    for chunk in file_handler_local.LocalFileHandler.read_file(file=image_2):
        checksum_image_2.update(chunk)

    # Create hexdigests
    checksum_image_1a_hex = checksum_image_1a.hexdigest()
    checksum_image_1b_hex = checksum_image_1b.hexdigest()
    checksum_image_2_hex = checksum_image_2.hexdigest()

    # Check that they are identical when they should be
    assert checksum_image_1a_hex == checksum_image_1b_hex
    assert checksum_image_1a_hex != checksum_image_2_hex != checksum_image_1b_hex

    # Make sure verify_checksum gives the same
    image_1a_verified, message1a = file_encryptor.Encryptor.verify_checksum(
        file=image_1a, correct_checksum=checksum_image_1a_hex
    )
    assert image_1a_verified and message1a == "File integrity verified."
    image_1b_verified, message1b = file_encryptor.Encryptor.verify_checksum(
        file=image_1b, correct_checksum=checksum_image_1b_hex
    )
    assert image_1b_verified and message1b == "File integrity verified."
    image_2_verified, message2 = file_encryptor.Encryptor.verify_checksum(
        file=image_1b, correct_checksum=checksum_image_1b_hex
    )
    assert image_2_verified and message2 == "File integrity verified."

    # Verify that verify_checksum fails to verify integrity
    fake_1_altered_verified, message1altered = file_encryptor.Encryptor.verify_checksum(
        file=image_1a, correct_checksum=checksum_image_2_hex
    )
    assert (
        not fake_1_altered_verified
        and message1altered
        == "Checksum verification failed. File '/home/runner/work/dds_cli/dds_cli/tests/images/test-image_1a.jpg' compromised."
    )


# - Csv files


def verify_files_csv(fs: FakeFilesystem, magnitude: str):
    """Perform checksum generation and verification for files of specific sizes."""
    # Specify number of lines to add
    num_lines: int = 0
    if magnitude == "less":
        num_lines = 100
    elif magnitude == "more":
        num_lines = 10000

    # Define lines to input
    cell_contents: str = "abcdefghijklmnopqrstuvwxyzåäö0123456789"
    row_contents: typing.List = [cell_contents] * 10
    file_contents: typing.List = [row_contents] * num_lines

    # Create fake files and verify that they have same size
    fake_file_path_1: pathlib.Path = pathlib.Path("small_text_file_1.csv")
    fake_file_path_2: pathlib.Path = pathlib.Path("small_text_file_2.csv")
    for file in [fake_file_path_1, fake_file_path_2]:
        fs.create_file(file)
        assert os.path.exists(file)
        with file.open(mode="w") as f:
            writer = csv.writer(f)
            writer.writerows(file_contents)
        if magnitude == "less":
            assert os.stat(file).st_size < FileSegment.SEGMENT_SIZE_RAW
        elif magnitude == "more":
            assert os.stat(file).st_size > FileSegment.SEGMENT_SIZE_RAW
    assert os.stat(fake_file_path_1).st_size == os.stat(fake_file_path_2).st_size

    # Generate checksums
    checksum_file_1 = hashlib.sha256()
    for chunk in file_handler_local.LocalFileHandler.read_file(file=fake_file_path_1):
        checksum_file_1.update(chunk)

    checksum_file_2 = hashlib.sha256()
    for chunk in file_handler_local.LocalFileHandler.read_file(file=fake_file_path_2):
        checksum_file_2.update(chunk)

    # Make sure they are identical
    checksum_hexdigest_1 = checksum_file_1.hexdigest()
    checksum_hexdigest_2 = checksum_file_2.hexdigest()
    assert checksum_hexdigest_1 == checksum_hexdigest_2

    # Make sure verify_checksum gives the same
    fake_1_verified, message1 = file_encryptor.Encryptor.verify_checksum(
        file=fake_file_path_1, correct_checksum=checksum_hexdigest_1
    )
    assert fake_1_verified and message1 == "File integrity verified."
    fake_2_verified, message2 = file_encryptor.Encryptor.verify_checksum(
        file=fake_file_path_2, correct_checksum=checksum_hexdigest_2
    )
    assert fake_2_verified and message2 == "File integrity verified."

    # Change one file slightly
    with fake_file_path_1.open(mode="a") as f:
        writer = csv.writer(f)
        writer.writerow(row_contents)
    assert os.stat(fake_file_path_1).st_size > os.stat(fake_file_path_2).st_size

    # Create new checksum for altered file
    checksum_file_1_altered = hashlib.sha256()
    for chunk in file_handler_local.LocalFileHandler.read_file(file=fake_file_path_1):
        checksum_file_1_altered.update(chunk)

    # Verify that checksum has changed
    checksum_hexdigest_1_altered = checksum_file_1_altered.hexdigest()
    assert checksum_hexdigest_1_altered != checksum_hexdigest_1

    # Verify that verify_checksum fails to verify integrity
    fake_1_altered_verified, message1altered = file_encryptor.Encryptor.verify_checksum(
        file=fake_file_path_1, correct_checksum=checksum_hexdigest_1
    )
    assert (
        not fake_1_altered_verified
        and message1altered
        == "Checksum verification failed. File 'small_text_file_1.csv' compromised."
    )


def test_verify_checksum_less_than_chunk_csv(fs: FakeFilesystem):
    """Check that the verify_checksum function verifies integrity when size less than 64 KiB."""
    verify_files_csv(fs=fs, magnitude="less")


def test_verify_checksum_more_than_chunk_csv(fs: FakeFilesystem):
    """Check that the verify_checksum function verifies integrity when size more than 64 KiB."""
    verify_files_csv(fs=fs, magnitude="more")


# public_to_hex


def test_public_to_hex_ok():
    """Verify that public key in hex is returned correctly."""
    # Generate keys
    private_key = asymmetric.x25519.X25519PrivateKey.generate()
    public_key = private_key.public_key()
    public_key_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )

    # Get public_key in hex
    public_hex: str = file_encryptor.ECDHKeyHandler.public_to_hex(public_key=public_key)
    assert isinstance(public_hex, str)
    assert public_hex == public_key_bytes.hex().upper()


def test_public_to_hex_not_ok():
    """Verify that public key in hex is returned correctly but that different keys don't match."""
    # Generate keys
    private_key_1 = asymmetric.x25519.X25519PrivateKey.generate()
    public_key_1 = private_key_1.public_key()

    private_key_2 = asymmetric.x25519.X25519PrivateKey.generate()
    public_key_2 = private_key_2.public_key()

    # Get public_key in hex
    public_hex_1: str = file_encryptor.ECDHKeyHandler.public_to_hex(public_key=public_key_1)
    public_hex_2: str = file_encryptor.ECDHKeyHandler.public_to_hex(public_key=public_key_2)

    assert public_hex_1 != public_hex_2


# get_public_component_hex


def test_get_public_component_hex_ok():
    """Verify that public key generated correctly from private key."""
    # Generate keys
    private_key = asymmetric.x25519.X25519PrivateKey.generate()
    public_key = private_key.public_key()
    public_key_hex = (
        public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        .hex()
        .upper()
    )

    # Get public_key in hex
    public_hex_from_function: str = file_encryptor.ECDHKeyHandler.get_public_component_hex(
        private_key=private_key
    )
    assert isinstance(public_hex_from_function, str)
    assert public_hex_from_function == public_key_hex


def test_get_public_component_hex_not_ok():
    """Two different private keys do not get the same public key."""
    # Generate keys
    private_key_1 = asymmetric.x25519.X25519PrivateKey.generate()
    private_key_2 = asymmetric.x25519.X25519PrivateKey.generate()

    # Get public_key in hex
    public_hex_1: str = file_encryptor.ECDHKeyHandler.get_public_component_hex(
        private_key=private_key_1
    )
    public_hex_2: str = file_encryptor.ECDHKeyHandler.get_public_component_hex(
        private_key=private_key_2
    )

    assert public_hex_1 != public_hex_2
