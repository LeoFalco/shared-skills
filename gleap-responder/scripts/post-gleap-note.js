import { readFile } from 'node:fs/promises'
import { resolve } from 'node:path'

const TICKET_ID = process.argv[2]
const PROJECT_ID = process.argv[3]
const CONTENT_FILE = process.argv[4]

if (!TICKET_ID || !PROJECT_ID || !CONTENT_FILE) {
  console.error('Usage: node post-gleap-note.js <ticket-id> <project-id> <content-file>')
  process.exit(1)
}

const GLEAP_API_KEY = process.env.GLEAP_API_KEY
if (!GLEAP_API_KEY) {
  console.error('Error: Missing GLEAP_API_KEY environment variable.\n')
  console.error('Add it to your shell profile so it is available in every session:')
  console.error('  echo \'export GLEAP_API_KEY=your_api_key_here\' >> ~/.zshrc  # macOS / Zsh')
  console.error('  echo \'export GLEAP_API_KEY=your_api_key_here\' >> ~/.bashrc # Linux / Bash')
  console.error('\nThen reload your shell: source ~/.zshrc (or ~/.bashrc)')
  process.exit(1)
}

/**
 * Converts plain text (with optional **bold** markdown) to TipTap doc format
 * used by Gleap's rich text editor.
 *
 * @param {string} text - Plain text content, may contain **bold** markers and newlines.
 * @returns {{ type: 'doc', content: Array<{ type: 'paragraph', content?: Array<{ type: 'text', text: string, marks?: Array<{ type: string }> }> }> }} TipTap document object.
 */
function textToTipTap (text) {
  const paragraphs = text.split('\n').map(line => {
    if (line.trim() === '') {
      return { type: 'paragraph' }
    }
    const parts = []
    const boldRegex = /\*\*(.+?)\*\*/g
    let lastIndex = 0
    let match
    while ((match = boldRegex.exec(line)) !== null) {
      if (match.index > lastIndex) {
        parts.push({ type: 'text', text: line.slice(lastIndex, match.index) })
      }
      parts.push({ type: 'text', text: match[1], marks: [{ type: 'bold' }] })
      lastIndex = boldRegex.lastIndex
    }
    if (lastIndex < line.length) {
      parts.push({ type: 'text', text: line.slice(lastIndex) })
    }
    if (parts.length === 0) {
      parts.push({ type: 'text', text: line })
    }
    return { type: 'paragraph', content: parts }
  })
  return { type: 'doc', content: paragraphs }
}


const res = await fetch('https://api.gleap.io/v3/messages', {
  method: 'POST',
  headers: {
    Authorization: `Bearer ${GLEAP_API_KEY}`,
    Project: PROJECT_ID,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    ticket: TICKET_ID,
    isNote: true,
    type: 'NOTE',
    comment: textToTipTap(await readFile(CONTENT_FILE, 'utf8'))
  })
})

if (!res.ok) {
  const body = await res.text()
  console.error(`Failed to post note: ${res.status} ${res.statusText}`)
  console.error(body)
  process.exit(1)
}

const result = await res.json()
console.log(`Internal note posted successfully on ticket ${TICKET_ID}`)
console.log(`Message ID: ${result._id || result.id || 'unknown'}`)
