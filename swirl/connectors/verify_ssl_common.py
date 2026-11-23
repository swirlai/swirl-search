from swirl.connectors.connector import Connector

from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

class VerifyCertsCommon(Connector):

    """Common to connectors that want to verify or turn off verification of certs"""
    """Extracts username, password and whether to verify certs and a path to the certs"""

    def __init__(self, provider_id, search_id, update, request_id=''):
        super().__init__(provider_id, search_id, update, request_id)

    ########################################
    def str_to_bool(self,s):
        return s.strip().lower() in ['true', '1', 'yes', 'y']

    def log_invalid_credentials(self, entry=None, entries=None):
        """Report that the SearchProvider's credentials could not be read:
        which comma-separated entry is wrong and what forms are accepted.
        The message does not repeat the credentials; it is written to the
        log and saved with the search's messages."""
        where = f"entry {entry} of {entries} is" if entry and entries else "an entry is"
        self.error(
            f"invalid credentials: {where} not in a recognised form. Expected "
            "username:password, bearer=<token>, verify_certs=<true or false> or "
            "ca_certs=<path>, separated by commas. The credentials themselves "
            "are not shown.")
        self.status = "ERR_INVALID_CREDENTIALS"

    def get_creds(self, def_verify_certs=False):

        cred_list = self.provider.credentials.split(',')

        uname=''
        pw=''
        ca_certs = ''
        bearer = ''
        verify_certs=def_verify_certs

        if not self.provider.credentials:
            return uname, pw, verify_certs, ca_certs, bearer

        entries = len(cred_list)
        for entry, cre in enumerate(cred_list, start=1):
            if cre.startswith('bearer='):
                # handle this special because tokens have '=' sign in them
                bearer = cre[len('bearer='):]
                if not bearer:
                    self.log_invalid_credentials(entry, entries)
                    break
            elif ':' in cre:
                (uname,pw) = cre.split(':')
                if not (uname and pw):
                    self.log_invalid_credentials(entry, entries)
                    break
            elif '=' in cre:
                # handle k=v type params
                (k,v) = cre.split('=')
                if not (k and v):
                    self.log_invalid_credentials(entry, entries)
                    break
                if k.strip().lower() == 'verify_certs':
                    verify_certs= self.str_to_bool(v)
                elif k.strip().lower() == 'ca_certs':
                    ca_certs = v.strip()
                else:
                    self.log_invalid_credentials(entry, entries)
                    break
            else:
                self.log_invalid_credentials(entry, entries)
                break

        return uname, pw, verify_certs, ca_certs, bearer
