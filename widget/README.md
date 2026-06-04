# ChatSite AI Widget

Drop-in vanilla-JS chat widget. < 30KB gzipped, Shadow DOM-isolated, SSE streaming.

## Build

```
npm install
npx esbuild widget.js --minify --target=es2018 --bundle > widget.min.js
```

## Embed

```html
<script src="https://cdn.chatsite.ai/widget.js" data-chatsite-id="CHATBOT_ID"></script>
<script>
  ChatSite.init({
    chatbotId: "CHATBOT_ID",
    position: "bottom-right",
    theme: "light",
    primaryColor: "#4F46E5",
    welcomeMessage: "Hi! How can I help?",
    suggestedQuestions: ["What do you do?", "Pricing?"]
  });
</script>
```

## Required CSP

Customers must add to their CSP:

```
script-src  'self' https://cdn.chatsite.ai
connect-src 'self' https://api.chatsite.ai
style-src   'self' 'unsafe-inline'  /* Shadow DOM scoped */
frame-ancestors 'none'
```

## Features

- Shadow DOM style isolation
- SSE streaming (server-sent events)
- LocalStorage history (last 50 messages)
- Lead capture form (after 3 messages or exit intent)
- ARIA roles, keyboard navigation
- Mobile full-screen below 480px
- Source citations in collapsible section
- No eval, no inline event handlers
