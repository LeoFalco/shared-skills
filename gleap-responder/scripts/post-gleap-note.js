import { readFile } from 'node:fs/promises'
import { resolve } from 'node:path'

// Load .env manually
try {
  const envPath = resolve(process.cwd(), '.env')
  const envContent = await readFile(envPath, 'utf8')
  for (const line of envContent.split('\n')) {
    const match = line.match(/^\s*([\w.-]+)\s*=\s*(.*)?\s*$/)
    if (match && !process.env[match[1]]) {
      process.env[match[1]] = (match[2] || '').replace(/^['"]|['"]$/g, '')
    }
  }
} catch {}

const TICKET_ID = process.argv[2]
const PROJECT_ID = process.argv[3]
const CONTENT_FILE = process.argv[4]

if (!TICKET_ID || !PROJECT_ID || !CONTENT_FILE) {
  console.error('Usage: node post-gleap-note.js <ticket-id> <project-id> <content-file>')
  process.exit(1)
}

const API_KEY = process.env.GLEAP_API_KEY
if (!API_KEY) {
  console.error('Missing GLEAP_API_KEY env var')
  process.exit(1)
}

const content = await readFile(CONTENT_FILE, 'utf8')

const res = await fetch('https://api.gleap.io/v3/messages', {
  method: 'POST',
  headers: {
    Authorization: `Bearer ${API_KEY}`,
    Project: PROJECT_ID,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    ticket: TICKET_ID,
    isNote: true,
    data: {
      content: {
        type: 'text',
        content: content
      }
    }
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
