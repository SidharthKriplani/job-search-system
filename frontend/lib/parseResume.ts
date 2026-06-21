/**
 * Client-side résumé parsing — PDF (pdf.js) and DOCX (mammoth), both in-browser
 * so the file never leaves the device until the user saves the extracted text.
 * Dynamic imports keep these heavy libs out of the SSR bundle.
 */

async function parsePdf(file: File): Promise<string> {
  const pdfjs: any = await import('pdfjs-dist')
  // Match the worker to the installed version (avoids version-skew errors).
  pdfjs.GlobalWorkerOptions.workerSrc =
    `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.mjs`
  const data = await file.arrayBuffer()
  const doc = await pdfjs.getDocument({ data }).promise
  let text = ''
  for (let i = 1; i <= doc.numPages; i++) {
    const page = await doc.getPage(i)
    const content = await page.getTextContent()
    text += content.items.map((it: any) => ('str' in it ? it.str : '')).join(' ') + '\n'
  }
  return text
}

async function parseDocx(file: File): Promise<string> {
  const mammoth: any = await import('mammoth')
  const arrayBuffer = await file.arrayBuffer()
  const { value } = await mammoth.extractRawText({ arrayBuffer })
  return value || ''
}

/** Returns extracted plain text, or throws with a user-friendly message. */
export async function parseResumeFile(file: File): Promise<string> {
  const name = file.name.toLowerCase()
  if (file.size > 8 * 1024 * 1024) throw new Error('File is too large (max 8 MB).')

  let text = ''
  if (name.endsWith('.pdf') || file.type === 'application/pdf') {
    text = await parsePdf(file)
  } else if (
    name.endsWith('.docx') ||
    file.type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
  ) {
    text = await parseDocx(file)
  } else {
    throw new Error('Please upload a PDF or DOCX file.')
  }

  // Collapse whitespace; PDFs especially come out with lots of stray spaces.
  text = text.replace(/[ \t]+/g, ' ').replace(/\n{3,}/g, '\n\n').trim()
  if (text.length < 30) {
    throw new Error('Could not extract text — if this is a scanned/image PDF, paste the text instead.')
  }
  return text
}
