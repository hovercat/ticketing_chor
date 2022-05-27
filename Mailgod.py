import datetime
import email.generator
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

    def __init__(
            self):  # TODO irgendwann umstellen sodass parameter uebergeben werden, OOOOODER dass das überhaupt kein objekt mehr ist
        self.mail_usr = MAIL_SECRETS['MAIL_USER']
        self.mail_pwd = MAIL_SECRETS['MAIL_PASSWORD']
        self.mail_host = MAIL_SECRETS['MAIL_HOST']
        self.mail_port = MAIL_SECRETS['MAIL_PORT']
        self._from = MAIL_SECRETS['MAIL_ADDRESS_SENDER']
        self._from_name = MAIL_NAME_SENDER
        self.log_file = MAIL_LOG_FILE
        self.log_dir = MAIL_LOG_DIR
        self.mail_sale_managers = MAIL_SALE_MANAGERS
        self.mail_off = MAILS_OFF

        if not os.path.isdir(self.log_dir):
            os.mkdir(self.log_dir)

    def send_mail(self, _to: list, _subject: str, _message: str, _bcc: list = [], _respond_to: str = None, file_name: str = None) -> None:
        with open(self.log_file, 'a', encoding='utf-8') as log:
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
                    try:
                        smtp.login(self.mail_usr, self.mail_pwd)
                    except smtplib.SMTPAuthenticationError as e:
                        log.write('[authentication failure]\n')
                        log.write('Exception: {}\n'.format(e))
                        raise e
                    log.write('[success]\n')

                    log.write('Attempting to send emails ')
                    if not self.mail_off:
                        try:
                            smtp.sendmail(self._from, [*_to, *_bcc], msg.as_string().encode('ascii'))
                            self.log_email(msg, file_name)
                            log.write('[success]\n')
                        except smtplib.SMTPRecipientsRefused as e:
                            log.write('[sender address fail]\n')
                            log.write('Mail-Address rejected by provider. Check for misspelling.\n')
                            log.write('Exception: {}\n'.format(e))
                            raise e
                    else:
                        log.write('[was just a test]\n')
                except smtplib.SMTPException as e:
                    log.write('[fail]\n')
                    log.write('Exception: {}\n'.format(e))
                    raise e
                except Exception as e:
                    raise e
                finally:
                    log.write('Connection closed.\n')
                    smtp.quit()

    def log_email(self, email_msg, file_name=None):
        if file_name is None:
            file_name = "out_mail_{}".format(datetime.datetime.now().strftime("%Y-%m-%d_%H_%S"))
        if not file_name.lower().endswith('.eml'):
            file_name = "{}.eml".format(file_name)

        with open(os.path.join(self.log_dir, file_name), 'w') as out_eml:
            gen = email.generator.Generator(out_eml)
            gen.flatten(email_msg)


