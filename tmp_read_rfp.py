from pypdf import PdfReader
p = r'C:\Users\maxtr\Downloads\Project 5 Request for Proposal (2).pdf'
r = PdfReader(p)
print(f'PAGES {len(r.pages)}')
for i, page in enumerate(r.pages):
    print(f'\n--- PAGE {i+1} ---\n{page.extract_text() or ""}')
