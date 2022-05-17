import datetime
import smtplib
import ssl
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from constants import *


class Mailgod:
    mail_usr: str
    mail_pwd: str
    mail_host: str
    mail_port: str
    log_file: str
    mail_sales_managers: []
    mail_off: bool
    _from: str
    _from_name: str

    def __init__(self): # TODO irgendwann umstellen sodass parameter uebergeben werden, OOOOODER dass das überhaupt kein objekt mehr ist
        self.mail_usr = MAIL_SECRETS['MAIL_USER']
        self.mail_pwd = MAIL_SECRETS['MAIL_PASSWORD']
        self.mail_host = MAIL_SECRETS['MAIL_HOST']
        self.mail_port = MAIL_SECRETS['MAIL_PORT']
        self._from = MAIL_SECRETS['MAIL_ADDRESS_SENDER']
        self._from_name = MAIL_NAME_SENDER
        self.log_file = MAIL_LOG_FILE
        self.mail_sale_managers = MAIL_SALE_MANAGERS
        self.mail_off = MAILS_OFF

    def send_mail(self, _to: list, _subject: str, _message: str, _bcc: list = [], _respond_to: str = None) -> None:
        with open(self.log_file, 'a') as log:
            #  Setup log entry
            log.write("===================================================================\n")
            log.write("{}\n".format(datetime.datetime.now().strftime('%d.%m.%Y, %H:%H:%S')))

            #  Setup mail message
            msg = MIMEMultipart()
            msg['Subject'] = _subject
            msg['To'] = ', '.join(_to)
            msg['Bcc'] = ', '.join(_bcc)
            from_header = formataddr((str(Header(self._from_name, 'utf-8')), self._from))
            msg['From'] = from_header
            if _respond_to is not None:
                msg.add_header('reply-to', _respond_to)
            # msg.set_content(_message)
            msg.attach(MIMEText(_message, "html"))

            #  Log mail
            log.writelines([
                "Contents:\n",
                "\tReceivers: {}\n".format(msg['To']),
                "\tBCC Receivers: {}\n".format(msg['Bcc']),
                "\tFrom Header: {}\n".format(msg['From']),
                "\tSubject: {}\n".format(msg['Subject']),
                "\tMSG: {}\n".format(_message)
            ])

            # Connect to mail host
            context = ssl.create_default_context()
            with smtplib.SMTP(self.mail_host, self.mail_port) as smtp:
                try:
                    log.write('Attempting connection to mail-provider ')
                    smtp.ehlo()
                    smtp.starttls(context=context)
                    smtp.ehlo()
                    smtp.login(self.mail_usr, self.mail_pwd)
                    log.write('[success]\n')

                    log.write('Attempting to send emails ')
                    if not self.mail_off:
                        smtp.sendmail(self._from, [*_to, *_bcc], msg.as_string())
                        log.write('[success]\n')
                    else:
                        log.write('[was just a test]\n')

                except smtplib.SMTPAuthenticationError as e:
                    log.write('[authentication failure]\n')
                    log.write('Exception: {}\n'.format(e))
                    raise e
                except smtplib.SMTPRecipientsRefused as e:
                    log.write('[sender address fail]\n')
                    log.write('Mail-Address rejected by provider. Check for misspelling.\n')
                    log.write('Exception: {}\n'.format(e))
                    raise e
                except smtplib.SMTPException as e:
                    log.write('[fail]\n')
                    log.write('Exception: {}\n'.format(e))
                    raise e
                finally:
                    log.write('Connection closed.\n')
                    smtp.quit()

