import smtplib
from email.header import Header
from email.message import EmailMessage
from email.utils import formataddr


def send_mail(mail_usr: str, mail_pwd: str, _from: str, _from_name: str, _respond_to: str, _to: list, _bcc: list, _subject: str, _message: str,
              host: str = 'localhost', port: int = 587) -> None:
    msg = EmailMessage()
    msg['Subject'] = _subject
    msg['To'] = ', '.join(_to)
    msg['Bcc'] = ', '.join(_bcc)
    from_header = formataddr((str(Header(_from_name, 'utf-8')), _from))
    msg['From'] = from_header
    msg.add_header('reply-to', _respond_to)
    msg.set_content(_message)

    s = smtplib.SMTP_SSL(host, port)
    s.ehlo()
    s.login(mail_usr, mail_pwd)
    try:
        s.sendmail(_from, [*_to, *_bcc], msg.as_string())
    except smtplib.SMTPRecipientsRefused:
        print('Email-address domain not exists!')
        raise
    finally:
        s.quit()

# send_mail('aschl@posteo.at', 'Ticketsystem TU Wien Chor', 'chor@tuwien.ac.at', ['aschl.uli@gmail.com'], [], 'HALLOULRICH!', 'HALLO\nKUHLRICH',
#          host='posteo.de',
#          port=465)
