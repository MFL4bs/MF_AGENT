with open('app.py', 'rb') as f:
    raw = f.read()

start = raw.find(b'def _generate_pdf(')
chunk = raw[start:start+7000]
with open('_pdf_chunk.txt', 'wb') as f:
    f.write(chunk)
print('done, size:', len(chunk))
