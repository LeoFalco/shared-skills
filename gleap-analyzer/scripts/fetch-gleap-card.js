import { writeFile } from 'node:fs/promises'

const TICKET_ID = process.argv[2]
const PROJECT_ID = process.argv[3]

if (!TICKET_ID || !PROJECT_ID) {
  console.error('Usage: node fetch-gleap-card.js <ticket-id> <project-id>')
  process.exit(1)
}

const HEX_24 = /^[0-9a-f]{24}$/i
if (!HEX_24.test(TICKET_ID)) {
  console.error(`Error: Invalid ticket ID "${TICKET_ID}". Must be a 24-character hex string.`)
  process.exit(1)
}
if (!HEX_24.test(PROJECT_ID)) {
  console.error(`Error: Invalid project ID "${PROJECT_ID}". Must be a 24-character hex string.`)
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

const BASE_URL = 'https://api.gleap.io/v3'
const headers = {
  Authorization: `Bearer ${GLEAP_API_KEY}`,
  Project: PROJECT_ID
}

async function apiGet (path, params = {}) {
  const url = new URL(`${BASE_URL}${path}`)
  for (const [k, v] of Object.entries(params)) url.searchParams.set(k, v)
  const res = await fetch(url, { headers })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}: ${await res.text()}`)
  return res.json()
}

async function fetchTicket () {
  return apiGet(`/tickets/${TICKET_ID}`)
}

async function fetchMessages (limit = 50, maxPages = 20) {
  const all = []

  for (let page = 0; page < maxPages; page++) {
    const data = await apiGet('/messages', {
      ticket: TICKET_ID,
      limit,
      skip: all.length,
      sort: 'createdAt_asc'
    })

    const messages = Array.isArray(data) ? data : data.messages || data.data || []
    all.push(...messages)

    if (messages.length < limit) break
  }

  return all
}

async function fetchActivities () {
  const data = await apiGet(`/tickets/${TICKET_ID}/activity-logs`)
  return Array.isArray(data) ? data : data.activities || data.data || []
}

function docToPlainText (node) {
  if (!node) return ''
  if (typeof node === 'string') return node
  if (node.type === 'text') return node.text || ''
  if (node.type === 'hardBreak') return '\n'
  if (node.type === 'imageBlock' || node.type === 'image') return ''
  const children = (node.content || []).map(docToPlainText).join('')
  if (node.type === 'paragraph') return children + '\n'
  return children
}

function simplifyMessageData (data) {
  if (!data) return data
  if (data.content?.type === 'doc') {
    return { ...data, content: docToPlainText(data.content).trim() }
  }
  return data
}

async function main () {
  console.log(`Fetching card history for ticket ${TICKET_ID}...`)

  const [ticket, messages, activities] = await Promise.all([
    fetchTicket(),
    fetchMessages(),
    fetchActivities()
  ])

  delete ticket.bot
  delete ticket.draftReply
  delete ticket.codingTask
  delete ticket.conversationClosed
  delete ticket.conversationClosedreturn
  delete ticket.formData
  delete ticket.archived
  delete ticket.isSpam
  delete ticket.tags
  delete ticket.slaBreached
  delete ticket.hidden
  delete ticket.needInitialPush
  delete ticket.noHumanInteraction
  delete ticket.snoozed
  delete ticket.queued
  delete ticket.trackerTicket
  delete ticket.mentions
  delete ticket.emailRefs
  delete ticket.session
  delete ticket.linkedTickets
  delete ticket.duplicatesCount
  delete ticket.sessions
  delete ticket.priority
  delete ticket.priorityOrder
  delete ticket.type
  delete ticket.sentiment
  delete ticket.status
  delete ticket.shareToken
  delete ticket.secretShareToken
  delete ticket.lexorank
  delete ticket.bugId
  delete ticket.project
  delete ticket.organisation
  delete ticket.generatingScreenshot
  delete ticket.screenshotRenderingFailed
  delete ticket.screenshotLive
  delete ticket.isSilent
  delete ticket.generatingReplay
  delete ticket.replayRenderingFailed
  delete ticket.replayLive
  delete ticket.originalEmailContent
  delete ticket.emailHeaders
  delete ticket.hasWebReplay
  delete ticket.integrationRefs
  delete ticket.attachments
  delete ticket.lastNotification
  delete ticket.faqSuggested
  delete ticket.notificationsUnread
  delete ticket.sessionNotificationsUnread
  delete ticket.hasAgentReply
  delete ticket.upvotesCount
  delete ticket.preventAutoReply
  delete ticket.copilotActions
  delete ticket.__v
  delete ticket.upvotes
  delete ticket.plan
  delete ticket.createdAt
  delete ticket.updatedAt
  delete ticket.firstAssignmentAt
  delete ticket.processingTeam
  if (ticket.form) {
    const sanitized = {}
    for (const [key, field] of Object.entries(ticket.form)) {
      sanitized[key] = {
        title: field.title,
        placeholder: field.placeholder,
        value: field.value
      }
    }
    ticket.form = sanitized
  }
  if (ticket.latestComment) {
    ticket.latestComment.data = simplifyMessageData(ticket.latestComment.data)
  }
  if (ticket.processingUser) {
    const u = ticket.processingUser
    ticket.processingUser = {
      name: `${u.firstName} ${u.lastName}`.trim(),
      email: u.email
    }
  }

  for (const msg of messages) {
    delete msg.reply
    delete msg.bot
    delete msg.ticket
    delete msg.organisation
    delete msg.project
    delete msg.sessionNotificationsUnread
    delete msg.statusHistory
    delete msg.isReply
    delete msg.kaiChat
    delete msg.sendToChannel
    delete msg.attachments
    delete msg.updatedAt
    delete msg.__v
    delete msg.index
    delete msg.fallbackUser
    delete msg.turnstileToken
    delete msg.notificationPreferences
    msg.data = simplifyMessageData(msg.data)
    if (msg.user) {
      msg.user = {
        name: `${msg.user.firstName} ${msg.user.lastName}`.trim(),
        email: msg.user.email
      }
    }
  }

  const filteredMessages = messages.filter(msg => msg.data?.content)

  const result = {
    ticket,
    messages: filteredMessages,
    activities
  }

  const outputFile = `gleap-card-${TICKET_ID}.json`
  await writeFile(outputFile, JSON.stringify(result, null, 2))

  console.log(`Ticket: ${ticket.title || ticket.summary || TICKET_ID}`)
  console.log(`Messages: ${filteredMessages.length}`)
  console.log(`Activities: ${activities.length}`)
  console.log(`Saved to ${outputFile}`)
}

main().catch(err => {
  console.error(err.message)
  process.exit(1)
})
