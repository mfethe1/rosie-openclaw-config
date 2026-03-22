#!/usr/bin/env python3
"""
Agent Mailbox - Targeted inter-agent messaging primitive.
Designed to supplement shared-state.json and broadcast monitors.
Implements the 'Agent Teams mailbox' primitive evaluated in P3 tasks.
"""
import json
import os
import sys
import datetime

MAILBOX_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'agent_mailbox.json')

def load_mailbox():
    if not os.path.exists(MAILBOX_FILE):
        return {}
    with open(MAILBOX_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_mailbox(data):
    with open(MAILBOX_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def send_message(from_agent, to_agent, subject, body):
    data = load_mailbox()
    if to_agent not in data:
        data[to_agent] = []
    
    msg = {
        "id": datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d%H%M%S%f'),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "from": from_agent,
        "subject": subject,
        "body": body,
        "read": False
    }
    data[to_agent].append(msg)
    save_mailbox(data)
    print(f"Message sent to {to_agent}")
    return msg["id"]

def read_messages(agent_name, unread_only=True):
    data = load_mailbox()
    messages = data.get(agent_name, [])
    if unread_only:
        messages = [m for m in messages if not m.get('read', False)]
    return messages

def mark_as_read(agent_name, message_id):
    data = load_mailbox()
    messages = data.get(agent_name, [])
    found = False
    for m in messages:
        if m.get('id') == message_id:
            m['read'] = True
            found = True
    if found:
        save_mailbox(data)
        return True
    return False

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: agent_mailbox.py [send|read|mark] ...")
        sys.exit(1)
        
    action = sys.argv[1]
    if action == 'send':
        if len(sys.argv) < 6:
            print("Usage: agent_mailbox.py send <from> <to> <subject> <body>")
            sys.exit(1)
        send_message(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
    elif action == 'read':
        if len(sys.argv) < 3:
            print("Usage: agent_mailbox.py read <agent_name> [--all]")
            sys.exit(1)
        unread_only = '--all' not in sys.argv
        msgs = read_messages(sys.argv[2], unread_only)
        print(json.dumps(msgs, indent=2))
    elif action == 'mark':
        if len(sys.argv) < 4:
            print("Usage: agent_mailbox.py mark <agent_name> <message_id>")
            sys.exit(1)
        if mark_as_read(sys.argv[2], sys.argv[3]):
            print(f"Message {sys.argv[3]} marked as read.")
        else:
            print(f"Message {sys.argv[3]} not found for {sys.argv[2]}.")
