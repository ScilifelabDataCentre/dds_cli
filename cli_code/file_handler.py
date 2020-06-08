def file_reader(file):
    for chunk in iter(lambda: file.read(65536), b''):
        yield chunk


def prep_upload(file):
    '''Prepares the files for upload'''

    with file.open(mode='rb') as f:
        chunk = file_reader(f)
        for c in chunk:
            print("----", c)

    sys.exit()
    # hash
    # _, checksum = gen_hmac(file=file)

    # encrypt
    # encrypted_file = self.tempdir.files / Path(file.name + ".c4gh")
    # try:
    #     original_umask = os.umask(0)
    #     with file.open(mode='rb') as orig:

    # except Exception as ee:
    #     return file, "Error", ee
    # finally:
    #     os.umask(original_umask)

    # return file, encrypted_file, checksum
