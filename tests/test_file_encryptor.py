import hashlib
import pathlib
import typing
from dds_cli import file_encryptor
from dds_cli import FileSegment
from dds_cli import file_handler_local
from pyfakefs.fake_filesystem import FakeFilesystem
import os 

def verify_files(fs: FakeFilesystem, magnitude: str):
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
    fake_1_verified, message1 = file_encryptor.Encryptor.verify_checksum(file=fake_file_path_1, correct_checksum=checksum_hexdigest_1)
    assert fake_1_verified and message1 == "File integrity verified."
    fake_2_verified, message2 = file_encryptor.Encryptor.verify_checksum(file=fake_file_path_2, correct_checksum=checksum_hexdigest_2)
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
    fake_1_altered_verified, message1altered = file_encryptor.Encryptor.verify_checksum(file=fake_file_path_1, correct_checksum=checksum_hexdigest_1)
    assert not fake_1_altered_verified and message1altered == "Checksum verification failed. File compromised."
def test_verify_checksum_less_than_chunk_textfile(fs: FakeFilesystem):
    """Check that the verify_checksum function verifies integrity when size less than 64 KiB."""
    verify_files(fs=fs, magnitude="less")

def test_verify_checksum_more_than_chunk_textfile(fs: FakeFilesystem):
    """Check that the verify_checksum function verifies integrity when size more than 64 KiB."""
    verify_files(fs=fs, magnitude="more")