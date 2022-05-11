import datetime
import smtplib
import ssl
from email.header import Header
from email.message import EmailMessage
from email.mime.text import MIMEText
from email.utils import formataddr


class Mailgod:
    mail_usr: str
    mail_pwd: str
    mail_host: str
    mail_port: str

    log_file: str

    _from: str
    _from_name: str

    def __init__(self, mail_usr: str, mail_pwd: str, mail_host: str, mail_port: int, _from: str, _from_name: str,
                 log_file: str):
        self.mail_usr = mail_usr
        self.mail_pwd = mail_pwd
        self.mail_host = mail_host
        self.mail_port = mail_port
        self._from = _from
        self._from_name = _from_name
        self.log_file = log_file

    def send_mail(self, _to: list, _subject: str, _message: str, _bcc: list = [], _respond_to: str = None) -> None:
        return

        with open(self.log_file, 'a') as log:
            #  Setup log entry
            log.write("===================================================================\n")
            log.write("{}\n".format(datetime.datetime.now().strftime('%d.%m.%Y, %H:%H:%S')))

            #  Setup mail message
            msg = EmailMessage()
            msg['Subject'] = _subject
            msg['To'] = ', '.join(_to)
            msg['Bcc'] = ', '.join(_bcc)
            from_header = formataddr((str(Header(self._from_name, 'utf-8')), self._from))
            msg['From'] = from_header
            if _respond_to is not None:
                msg.add_header('reply-to', _respond_to)
            msg.set_content(_message)

            #  Log mail
            log.writelines([
                "Contents:\n",
                "\tReceivers: {}\n".format(msg['To']),
                "\tBCC Receivers: {}\n".format(msg['Bcc']),
                "\tFrom Header: {}\n".format(msg['From']),
                "\tContent: {}\n".format(_message)
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

                    log.write('Attempting to send email_templates ')
                    smtp.sendmail(self._from, [*_to, *_bcc], msg.as_string())
                    log.write('[success]\n')

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


import mail_secrets as ms

if __name__ == '__main__':
    mailgod = Mailgod(ms.user, "asdf", ms.host, ms.port, ms.address_sender, ms.name_sender,
                      '/home/ulrichaschl/mails.log')
    mailgod.send_mail(['ulrich.aschl@gmail.cdfom'], 'TODWICHTIG', 'eine_nachricht')
