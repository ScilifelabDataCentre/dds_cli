import datetime
import os

import pytest

from dds_cli.exceptions import TokenDeserializationError, TokenExpirationMissingError
from dds_cli.utils import (
    get_token_expiration_time,
    get_token_header_contents,
    readable_timedelta,
    delete_folder,
)

sample_fully_authenticated_token = (
    "eyJhbGciOiJBMjU2S1ciLCJlbmMiOiJBMjU2R0"
    "NNIiwiZXhwIjoiMjAyMi0wMi0yNFQxNDo1MTow"
    "Ni4yMTg3OTgifQ.Ul5rfhy0S9iaX2dPGH93HtL"
    "-3tVdGBdAzzoTQXb_QJrcIIA0wEwdQw.95ii5p"
    "anPoIUV1Mf.cAwnDuri4kxjwnQfY48pS0rZ-ob"
    "-RnKBacUcOe0l3RJrMCbc2nfkdkzc7KBH06ESi"
    "D-I7MU-U6270uLa2M4ZcLk0AkCZ3S7xrm9-bDu"
    "_73yCDCIQravwphlxCVSSrNQUPU8BonwBuDu-5"
    "WjuJyL_zC7MBcduxau8L0Hpk0IOLfIDgEtq9uR"
    "ELIxjbw1-YEhOtUBKm3E3jevmohgCt7RqcbbuB"
    "ZtZgYSm5NjOO1XhHBz_kZo1lhONNVVDNUkAoAP"
    "FoJ7WOAPajCGiDi8yyq7e-ojcxoSf0gl5NVd25"
    "cmO7i4OqsXB9VNlN5asEZE4WXAmVrQTppCbTG_"
    "9te04fCDwGabzDqtdfUqX-d_yaQ_UYHmJMN1xc"
    "4aF-uWZtk3loyMZU-uedQPqsJSZ.ay0MIzbtmt"
    "GsxUm2blaKUA"
)

token_without_exp_claim_in_header = (
    "eyJhbGciOiJBMjU2S1ciLCJlbmMiOiJBMjU2R"
    "0NNIn0.3H7fZh-rxkSuERSgknz4fOtseDn6PN"
    "c0RR-1IU8EmoTfpOuMOTvVbg.a_UwR9ArB6kn"
    "1LEB.7Ko4g1Xs9S_EQsAbGCtc96x_h3P6lwZz"
    "_X6t1EKA-EFeLXgwjAHuX5S_rC7YK28rqIT_m"
    "9FQABgTSgi0nBHCUurPA43U2P2mDR9UOvCHFY"
    "QXLKyO3M-ykVrmNwSGZMjo3HHrmcuICiwiH7l"
    "boGl5Vr-iSFpyyuy33thSrlwfutI80sKe3RSm"
    "Kup_Mh7tM0mw0WbQezfAcNR_52BeP_ncbVxFl"
    "714ikyo2HCk0bKREIpetdaKCaoZgqlhOarlAU"
    "GwPaKtdgmXb7Ef4VKfYdnLIxqzv3RtVmZiEb1"
    "L-xCS4vnwXvw_bEa_QU-5HfyLYOszjAHiYHxr"
    "q8v1xnfoyWfd20OxQMhYueVzlPw1HfMSfvCNV"
    "LZO-vNNKHTaGnPyGuykhMNScIgkR1l8.TEp4L"
    "s4c29JtGogmdYbTbw"
)


def test_get_token_expiration_time_successful():
    exp_claim_in_token_header = get_token_expiration_time(token=sample_fully_authenticated_token)
    assert isinstance(datetime.datetime.fromisoformat(exp_claim_in_token_header), datetime.datetime)


def test_get_token_expiration_time_exception():
    with pytest.raises(TokenExpirationMissingError) as error:
        get_token_expiration_time(token=token_without_exp_claim_in_header)

    assert "Expiration time could not be found in the header of the token." in str(error.value)


def test_get_token_header_contents_exception():
    with pytest.raises(TokenDeserializationError) as error:
        get_token_header_contents(token="not.a.token")

    assert "Token could not be deserialized." in str(error.value)

    with pytest.raises(TokenDeserializationError) as error:
        get_token_header_contents(token="notatoken")

    assert "Token could not be deserialized." in str(error.value)

    with pytest.raises(TokenDeserializationError) as error:
        get_token_header_contents(token="not.a.token.not.a")

    assert "Token could not be deserialized." in str(error.value)


def test_readable_timedelta():
    # at the time of writing this test, negative values are not passed in, but the function already supports it
    assert readable_timedelta(datetime.timedelta(seconds=-60)) == "1 minute"
    assert readable_timedelta(datetime.timedelta(milliseconds=-100)) == "less than a minute"

    assert readable_timedelta(datetime.timedelta(milliseconds=100)) == "less than a minute"
    assert readable_timedelta(datetime.timedelta(seconds=59)) == "less than a minute"
    assert readable_timedelta(datetime.timedelta(seconds=60)) == "1 minute"
    assert readable_timedelta(datetime.timedelta(minutes=1)) == "1 minute"
    assert readable_timedelta(datetime.timedelta(seconds=98765)) == "1 day 3 hours 26 minutes"
    assert readable_timedelta(datetime.timedelta(hours=3)) == "3 hours"
    assert readable_timedelta(datetime.timedelta(days=1)) == "1 day"


def test_delete_folder(fs):
    fs.create_dir("folder")
    fs.create_file("folder/file")
    assert os.path.isdir("folder") == True
    delete_folder("folder")
    assert os.path.isdir("folder") == False
