from flask import Flask, request, jsonify
import imaplib
import email
import re

app = Flask(__name__)

# Gmail IMAP server details
IMAP_SERVER = 'imap.gmail.com'
IMAP_PORT = 993

# Email account credentials (should use environment variables in production)
EMAIL_ACCOUNT = 'stephenpeculiahr@gmail.com'
APP_PASSWORD = 'wpobqoiuudpupajt'

def extract_email_parameter(header, parameter):
    if parameter == 'message_id':
        return header.get('Message-ID', '')

    elif parameter == 'received_spf':
        return header.get('Received-SPF', '')

    elif parameter == 'authentication_results':
        return header.get('Authentication-Results', '')

    elif parameter == 'from':
        return header.get('From', '')

    elif parameter == 'return_path':
        return header.get('Return-Path', '')

    elif parameter == 'domain_from_return_path':
        return extract_domain_from_return_path(header.get('Return-Path', ''))

    elif parameter == 'ip_from_received_spf':
        return extract_ip_from_received_spf(header.get('Received-SPF', ''))

    return ''

def extract_domain_from_return_path(return_path):
    match = re.search(r'@([A-Za-z0-9.-]+)>', return_path)
    if match:
        return match.group(1)
    return ''

def extract_ip_from_received_spf(received_spf):
    match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', received_spf)
    if match:
        return match.group(1)
    return ''

def list_labels(mail):
    status, labels = mail.list()
    if status == 'OK':
        label_list = []
        for label in labels:
            label_list.append(label.decode().split(' "/" ')[-1].replace('"', ''))
        return label_list
    else:
        return []

@app.route('/list_labels', methods=['GET'])
def list_email_labels():
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(EMAIL_ACCOUNT, APP_PASSWORD)
        labels = list_labels(mail)
        mail.logout()
        return jsonify({'labels': labels}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/extract_parameter', methods=['POST'])
def extract_parameter():
    data = request.json
    label = data.get('label')
    parameter = data.get('parameter')

    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(EMAIL_ACCOUNT, APP_PASSWORD)
        mail.select(f'"{label}"', readonly=True)
        
        # Search for emails and extract parameter
        status, messages = mail.search(None, 'ALL')
        email_ids = messages[0].split()
        result = []

        for e_id in email_ids:
            status, msg_data = mail.fetch(e_id, '(BODY.PEEK[HEADER.FIELDS (Message-ID Received-SPF Authentication-Results From Return-Path)])')
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    extracted_value = extract_email_parameter(msg, parameter)
                    result.append(extracted_value)

        mail.logout()
        return jsonify({'result': result}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
