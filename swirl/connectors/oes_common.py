from swirl.connectors.connector import Connector

class OpenElasticCommon(Connector):

    """ Code common to both open search and elastic connectors"""

    def __init__(self, provider_id, search_id, update, request_id=''):
        super().__init__(provider_id, search_id, update, request_id)

    ########################################
    def str_to_bool(self,s):
        return s.strip().lower() in ['true', '1', 'yes', 'y']

    def log_invalid_credentials(self):
        self.error("invalid credentials: {self.provider.credentials}")
        self.status = "ERR_INVALID_CREDENTIALS"

    def get_creds(self):

        if not self.provider.credentials:
            self.error("no credentials: {self.provider.credentials}")
            self.status = "ERR_NO_CREDENTIALS"
            return

        cred_list = self.provider.credentials.split(',')
        uname=''
        pw=''
        ca_certs = ''
        verify_certs=False
        for cre in cred_list:
            if ':' in cre:
                (uname,pw) = cre.split(':')
                if not (uname and pw):
                    self.log_invalid_credentials()
                    break
            elif '=' in cre:
                (k,v) = cre.split('=')
                if not (k and v):
                    self.log_invalid_credentials()
                    break
                if k.strip().lower() == 'verify_certs':
                    verify_certs= self.str_to_bool(v)
                elif k.strip().lower() == 'ca_certs':
                    ca_certs = v.strip()
                else:
                    self.log_invalid_credentials()
                    break
            else:
                self.log_invalid_credentials()
                break

        return uname,pw,verify_certs,ca_certs
