"""Local export of verified, published fiction only, using the Python standard library."""
from html import escape
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED, ZIP_STORED
import re
import soul_chronicle as c
import soul_reader as reader

MAX_CHARS=15_000_000

def chapters(db):
    if not c.canon_ok(db):raise ValueError("canon integrity")
    import soul_novel
    numbers=list(range(1,14))+[n for n, in db.execute("SELECT a.number FROM saga_arcs a JOIN chronicle_drafts d ON a.draft_id=d.id WHERE a.number IS NOT NULL AND d.status='approved' ORDER BY a.number")]
    total=0;seen=set()
    for n in numbers:
        if n in seen:continue
        group=soul_novel.group_for(db,n)
        nums=[r["number"] for r in group] if group else [n]
        sources=[reader.source(db,k) for k in nums]
        body="\n\n".join(s["body"] for s in sources)
        total+=len(body)
        if total>MAX_CHARS:raise ValueError("export too large")
        seen.update(nums)
        yield nums[0],sources[0]["title"],body

def paragraphs(body):
    for line in body.splitlines():
        if not line.strip():continue
        if line.startswith("#### "):yield "heading",line[5:]
        elif line.startswith("### "):yield "heading",line[4:]
        elif line.startswith(">"):yield "quote",line[1:].strip()
        elif line=="---":yield "separator","⁂"
        else:yield "text",line

def inline_parts(text):
    pattern=r"(\*\*[^*\n]+\*\*|(?<!\*)\*[^*\n]+\*(?!\*))"
    for part in re.split(pattern,text):
        if part.startswith("**") and part.endswith("**") and len(part)>4:yield "bold",part[2:-2]
        elif part.startswith("*") and part.endswith("*") and len(part)>2:yield "italic",part[1:-1]
        elif part:yield "",part

def inline_html(text):
    tags={"bold":"strong","italic":"em"}
    return "".join(f"<{tags[k]}>{escape(v)}</{tags[k]}>" if k else escape(v) for k,v in inline_parts(text))

def html_section(n,title,body):
    out=[f'<section id="ch{n}"><h1>{n}. {escape(title)}</h1>']
    for kind,line in paragraphs(body):
        if not line:continue
        tag="h2" if kind=="heading" else "p"
        out.append(f'<{tag} class="{kind}">{inline_html(line)}</{tag}>')
    out.append("</section>")
    return "\n".join(out)

def html_book(rows):
    contents="".join(f'<li><a href="#ch{n}">{n}. {escape(title)}</a></li>' for n,title,_ in rows)
    return ('<!doctype html><html lang="ru"><head><meta charset="utf-8"><title>Hakureya</title><style>'
        '@page{size:A4;margin:22mm}body{max-width:170mm;margin:20px auto;color:#222;background:white;font:12pt/1.6 Georgia,serif;padding:12px}'
        'h1,h2{line-height:1.3}section{break-before:page}h2{break-after:avoid}.quote{margin-left:1.5em;font-style:italic}.separator{text-align:center}'
        'a{color:inherit}@media print{body{padding:0;margin:0}a{text-decoration:none}}</style></head><body>'
        '<h1>HAKUREYA</h1><p>Летопись Белоснежной Императрицы · опубликованные главы</p><p>Печать в PDF: Ctrl+P → Сохранить как PDF.</p>'
        '<h2>Оглавление</h2><ol>'+contents+'</ol>'+"".join(html_section(*r) for r in rows)+'</body></html>').encode("utf-8")

def epub(rows):
    buf=BytesIO()
    with ZipFile(buf,"w",compression=ZIP_DEFLATED) as z:
        z.writestr("mimetype","application/epub+zip",compress_type=ZIP_STORED)
        z.writestr("META-INF/container.xml",'<?xml version="1.0" encoding="UTF-8"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="OEBPS/book.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')
        manifest=['<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>']
        spine=[]
        nav=[]
        for n,title,body in rows:
            name=f"ch{n}.xhtml"
            z.writestr("OEBPS/"+name,'<?xml version="1.0" encoding="UTF-8"?><html xmlns="http://www.w3.org/1999/xhtml" lang="ru"><head><title>'+escape(title)+'</title></head><body>'+html_section(n,title,body)+'</body></html>')
            manifest.append(f'<item id="ch{n}" href="{name}" media-type="application/xhtml+xml"/>')
            spine.append(f'<itemref idref="ch{n}"/>')
            nav.append(f'<li><a href="{name}">{n}. {escape(title)}</a></li>')
        z.writestr("OEBPS/nav.xhtml",'<?xml version="1.0" encoding="UTF-8"?><html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><head><title>Оглавление</title></head><body><nav epub:type="toc" id="toc"><h1>Оглавление</h1><ol>'+"".join(nav)+'</ol></nav></body></html>')
        from datetime import datetime,timezone
        updated=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        z.writestr("OEBPS/book.opf",'<?xml version="1.0" encoding="UTF-8"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="bookid">urn:hakureya:local-edition</dc:identifier><dc:title>HAKUREYA</dc:title><dc:language>ru</dc:language><meta property="dcterms:modified">'+updated+'</meta></metadata><manifest>'+"".join(manifest)+'</manifest><spine>'+"".join(spine)+'</spine></package>')
    return buf.getvalue()

def docx(rows):
    def p(value,style="",page=False):
        props=('<w:pStyle w:val="'+style+'"/>' if style else '')+('<w:pageBreakBefore/>' if page else '')
        runs="".join('<w:r>'+('<w:rPr><w:b/></w:rPr>' if k=="bold" else '<w:rPr><w:i/></w:rPr>' if k=="italic" else '')+'<w:t xml:space="preserve">'+escape(v)+'</w:t></w:r>' for k,v in inline_parts(value))
        return '<w:p>'+('<w:pPr>'+props+'</w:pPr>' if props else '')+runs+'</w:p>'
    out=[p("HAKUREYA","Title"),p("Летопись Белоснежной Императрицы")]
    for n,title,body in rows:
        out.append(p(f"{n}. {title}","Heading1",True))
        for kind,line in paragraphs(body):
            if line:out.append(p(line,"Heading2" if kind=="heading" else "Quote" if kind=="quote" else ""))
    buf=BytesIO()
    with ZipFile(buf,"w",compression=ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml",'<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>')
        z.writestr("_rels/.rels",'<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
        z.writestr("word/_rels/document.xml.rels",'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>')
        z.writestr("word/styles.xml",'<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/><w:sz w:val="24"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:spacing w:after="120" w:line="360" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>'+''.join('<w:style w:type="paragraph" w:styleId="'+name+'"><w:name w:val="'+name+'"/><w:rPr>'+('<w:i/>' if name=="Quote" else '<w:b/><w:sz w:val="'+size+'"/>')+'</w:rPr></w:style>' for name,size in (("Title","44"),("Heading1","32"),("Heading2","28"),("Quote","24")))+'</w:styles>')
        z.writestr("word/document.xml",'<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'+"".join(out)+'<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134" w:header="567" w:footer="567" w:gutter="0"/></w:sectPr></w:body></w:document>')
    return buf.getvalue()

def export(db,kind):
    rows=list(chapters(db))
    if kind=="epub":return epub(rows),"application/epub+zip","Hakureya.epub"
    if kind=="docx":return docx(rows),"application/vnd.openxmlformats-officedocument.wordprocessingml.document","Hakureya.docx"
    if kind=="html":return html_book(rows),"text/html; charset=utf-8",None
    raise ValueError("unknown export")
