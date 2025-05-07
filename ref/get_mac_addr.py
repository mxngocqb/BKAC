import uuid
mac = ':'.join(reversed([f'{(uuid.getnode() >> i) & 0xff:02x}' for i in range(0, 48, 8)]))

print(mac)