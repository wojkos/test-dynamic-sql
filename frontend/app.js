// Navigation handling
const navItems = document.querySelectorAll('.nav-item');
const sections = document.querySelectorAll('.content-section');

navItems.forEach(item => {
    item.addEventListener('click', () => {
        const targetSection = item.getAttribute('data-section');

        // Update active nav item
        navItems.forEach(nav => nav.classList.remove('active'));
        item.classList.add('active');

        // Update active section
        sections.forEach(section => section.classList.remove('active'));
        document.getElementById(`${targetSection}-section`).classList.add('active');

        // Load data for the section if needed
        if (targetSection === 'schema') {
            loadSchema();
        } else if (targetSection === 'raw-data') {
            loadTableList();
        }
    });
});

// Chat functionality
const chatContainer = document.getElementById('chat-container');
const chatForm = document.getElementById('chat-form');
const userInput = document.getElementById('user-input');

chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const question = userInput.value.trim();
    if (!question) return;

    // Add user message
    appendMessage(question, 'user');
    userInput.value = '';

    // Show loading state
    const loadingId = appendLoadingMessage();

    try {
        const response = await fetch('/query', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ question })
        });

        const data = await response.json();

        // Remove loading message
        removeMessage(loadingId);

        if (!response.ok) {
            appendMessage(`Error: ${data.detail || 'Something went wrong'}`, 'bot', true);
            return;
        }

        if (data.error) {
            appendMessage(`Error: ${data.error}`, 'bot', true);
            // Even if error, maybe show SQL if available?
            if (data.sql) {
                appendSql(data.sql);
            }
            return;
        }

        // 1. Show Data
        if (data.data && data.data.length > 0) {
            appendTable(data.data);
        } else {
            appendMessage("No results found.", 'bot');
        }

        // 2. Show SQL (as requested)
        if (data.sql) {
            appendSql(data.sql);
        }

    } catch (error) {
        removeMessage(loadingId);
        appendMessage(`Network Error: ${error.message}`, 'bot', true);
    }
});

function appendMessage(text, sender, isError = false) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${sender}-message`;

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    if (isError) contentDiv.classList.add('error-msg');
    contentDiv.textContent = text;

    msgDiv.appendChild(contentDiv);
    chatContainer.appendChild(msgDiv);
    scrollToBottom();
    return msgDiv;
}

function appendLoadingMessage() {
    const id = 'loading-' + Date.now();
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message bot-message';
    msgDiv.id = id;

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.textContent = 'Thinking...';

    msgDiv.appendChild(contentDiv);
    chatContainer.appendChild(msgDiv);
    scrollToBottom();
    return id;
}

function removeMessage(id) {
    const element = document.getElementById(id);
    if (element) {
        element.remove();
    }
}

function appendSql(sql) {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message bot-message';

    const sqlBlock = document.createElement('div');
    sqlBlock.className = 'sql-block';

    const label = document.createElement('div');
    label.className = 'sql-label';
    label.textContent = 'Generated SQL';

    const code = document.createElement('code');
    code.textContent = sql;

    sqlBlock.appendChild(label);
    sqlBlock.appendChild(code);

    msgDiv.appendChild(sqlBlock);
    chatContainer.appendChild(msgDiv);
    scrollToBottom();
}

function appendTable(data) {
    if (!data || data.length === 0) return;

    const msgDiv = document.createElement('div');
    msgDiv.className = 'message bot-message';

    const tableContainer = document.createElement('div');
    tableContainer.className = 'data-table-container';

    const table = document.createElement('table');
    const thead = document.createElement('thead');
    const tbody = document.createElement('tbody');

    // Header
    const headers = Object.keys(data[0]);
    const trHead = document.createElement('tr');
    headers.forEach(h => {
        const th = document.createElement('th');
        // Capitalize first letter
        th.textContent = h.charAt(0).toUpperCase() + h.slice(1);
        trHead.appendChild(th);
    });
    thead.appendChild(trHead);

    // Body
    data.forEach(row => {
        const tr = document.createElement('tr');
        headers.forEach(h => {
            const td = document.createElement('td');
            td.textContent = row[h];
            tr.appendChild(td);
        });
        tbody.appendChild(tr);
    });

    table.appendChild(thead);
    table.appendChild(tbody);
    tableContainer.appendChild(table);

    msgDiv.appendChild(tableContainer);
    chatContainer.appendChild(msgDiv);
    scrollToBottom();
}

function scrollToBottom() {
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

// Schema Section
let schemaData = null;

async function loadSchema() {
    const schemaContainer = document.getElementById('schema-container');

    // Only load if not already loaded
    if (schemaData) {
        return;
    }

    schemaContainer.innerHTML = '<div class="loading-state">Loading schema...</div>';

    try {
        const response = await fetch('/schema');
        const data = await response.json();

        if (data.error) {
            schemaContainer.innerHTML = `<div class="empty-state">Error: ${data.error}</div>`;
            return;
        }

        schemaData = data.schema;
        displaySchema(schemaData);
    } catch (error) {
        schemaContainer.innerHTML = `<div class="empty-state">Error loading schema: ${error.message}</div>`;
    }
}

function displaySchema(schema) {
    const schemaContainer = document.getElementById('schema-container');
    schemaContainer.innerHTML = '';

    schema.forEach(table => {
        const tableDiv = document.createElement('div');
        tableDiv.className = 'schema-table';

        // Table header
        const headerDiv = document.createElement('div');
        headerDiv.className = 'schema-table-header';
        headerDiv.innerHTML = `
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M3 3H21V21H3V3Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M3 9H21" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M9 21V9" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <span class="schema-table-name">${table.table_name}</span>
        `;

        // Columns
        const columnsDiv = document.createElement('div');
        columnsDiv.className = 'schema-columns';

        table.columns.forEach(col => {
            const colDiv = document.createElement('div');
            colDiv.className = 'schema-column';

            const nameSpan = document.createElement('span');
            nameSpan.className = 'column-name';
            nameSpan.textContent = col.name;

            const typeSpan = document.createElement('span');
            typeSpan.className = 'column-type';
            typeSpan.textContent = col.type;

            const badgesDiv = document.createElement('div');
            badgesDiv.style.display = 'flex';
            badgesDiv.style.gap = '0.5rem';

            if (col.primary_key) {
                const pkBadge = document.createElement('span');
                pkBadge.className = 'column-badge badge-pk';
                pkBadge.textContent = 'PK';
                badgesDiv.appendChild(pkBadge);
            }

            if (col.nullable) {
                const nullBadge = document.createElement('span');
                nullBadge.className = 'column-badge badge-nullable';
                nullBadge.textContent = 'NULL';
                badgesDiv.appendChild(nullBadge);
            }

            colDiv.appendChild(nameSpan);
            colDiv.appendChild(typeSpan);
            colDiv.appendChild(badgesDiv);
            colDiv.appendChild(document.createElement('span')); // Empty span for grid alignment

            columnsDiv.appendChild(colDiv);
        });

        tableDiv.appendChild(headerDiv);
        tableDiv.appendChild(columnsDiv);
        schemaContainer.appendChild(tableDiv);
    });
}

// Raw Data Section
const tableSelect = document.getElementById('table-select');
const rawDataContainer = document.getElementById('raw-data-container');

async function loadTableList() {
    // Use schema data if available, otherwise fetch it
    if (!schemaData) {
        try {
            const response = await fetch('/schema');
            const data = await response.json();
            schemaData = data.schema;
        } catch (error) {
            console.error('Error loading table list:', error);
            return;
        }
    }

    // Populate table select
    tableSelect.innerHTML = '<option value="">-- Select a table --</option>';
    schemaData.forEach(table => {
        const option = document.createElement('option');
        option.value = table.table_name;
        option.textContent = table.table_name;
        tableSelect.appendChild(option);
    });
}

tableSelect.addEventListener('change', async (e) => {
    const tableName = e.target.value;

    if (!tableName) {
        rawDataContainer.innerHTML = '<div class="empty-state">Select a table to view its data.</div>';
        return;
    }

    rawDataContainer.innerHTML = '<div class="loading-state">Loading data...</div>';

    try {
        const response = await fetch(`/tables/${tableName}/data`);
        const data = await response.json();

        if (data.error) {
            rawDataContainer.innerHTML = `<div class="empty-state">Error: ${data.error}</div>`;
            return;
        }

        displayRawData(data.data, tableName);
    } catch (error) {
        rawDataContainer.innerHTML = `<div class="empty-state">Error loading data: ${error.message}</div>`;
    }
});

function displayRawData(data, tableName) {
    rawDataContainer.innerHTML = '';

    if (!data || data.length === 0) {
        rawDataContainer.innerHTML = '<div class="empty-state">No data found in this table.</div>';
        return;
    }

    const containerDiv = document.createElement('div');
    containerDiv.className = 'raw-data-table-container';

    // Header
    const headerDiv = document.createElement('div');
    headerDiv.className = 'raw-data-table-header';
    headerDiv.innerHTML = `
        <div class="raw-data-table-title">${tableName}</div>
        <div class="raw-data-table-count">${data.length} row${data.length !== 1 ? 's' : ''}</div>
    `;

    // Table
    const tableWrapper = document.createElement('div');
    tableWrapper.className = 'raw-data-table';

    const table = document.createElement('table');
    const thead = document.createElement('thead');
    const tbody = document.createElement('tbody');

    // Header
    const headers = Object.keys(data[0]);
    const trHead = document.createElement('tr');
    headers.forEach(h => {
        const th = document.createElement('th');
        th.textContent = h.charAt(0).toUpperCase() + h.slice(1);
        trHead.appendChild(th);
    });
    thead.appendChild(trHead);

    // Body
    data.forEach(row => {
        const tr = document.createElement('tr');
        headers.forEach(h => {
            const td = document.createElement('td');
            td.textContent = row[h] !== null ? row[h] : 'NULL';
            tr.appendChild(td);
        });
        tbody.appendChild(tr);
    });

    table.appendChild(thead);
    table.appendChild(tbody);
    tableWrapper.appendChild(table);

    containerDiv.appendChild(headerDiv);
    containerDiv.appendChild(tableWrapper);
    rawDataContainer.appendChild(containerDiv);
}

// ============================================================
// MCP CHAT FUNCTIONALITY
// ============================================================

const mcpChatContainer = document.getElementById('mcp-chat-container');
const mcpChatForm = document.getElementById('mcp-chat-form');
const mcpUserInput = document.getElementById('mcp-user-input');

// Session management for context persistence
let mcpSessionId = null;

// Function to start a new chat (clear session)
async function startNewMcpChat() {
    if (mcpSessionId) {
        try {
            await fetch(`/mcp-chat/session/${mcpSessionId}`, { method: 'DELETE' });
        } catch (e) {
            console.log('Could not clear session on server:', e);
        }
    }
    mcpSessionId = null;
    mcpChatContainer.innerHTML = `
        <div class="welcome-message">
            <p>Chat with an AI that uses MCP tools for database queries. Ask anything!</p>
            <p class="hint">Try: "Show all employees", then follow up with "Which ones are in Engineering?"</p>
        </div>
    `;
}

mcpChatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const message = mcpUserInput.value.trim();
    if (!message) return;

    // Add user message
    appendMcpMessage(message, 'user');
    mcpUserInput.value = '';

    // Show loading state
    const loadingId = appendMcpLoadingMessage();

    try {
        // Include session_id if we have one for context persistence
        const requestBody = { message };
        if (mcpSessionId) {
            requestBody.session_id = mcpSessionId;
        }

        const response = await fetch('/mcp-chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody)
        });

        const data = await response.json();

        // Remove loading message
        removeMcpMessage(loadingId);

        if (!response.ok) {
            appendMcpMessage(`Error: ${data.detail || 'Something went wrong'}`, 'bot', true);
            return;
        }

        // Store session ID for future messages
        if (data.session_id) {
            mcpSessionId = data.session_id;
        }

        // Display response based on type
        if (data.type === 'mcp_tool') {
            // MCP tool was used - show badge, data, and response
            appendMcpToolResponse(data);
        } else {
            // Direct response - no MCP tool used
            appendMcpDirectResponse(data.response);
        }

    } catch (error) {
        removeMcpMessage(loadingId);
        appendMcpMessage(`Network Error: ${error.message}`, 'bot', true);
    }
});

function appendMcpMessage(text, sender, isError = false) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${sender}-message`;

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    if (isError) contentDiv.classList.add('error-msg');
    contentDiv.textContent = text;

    msgDiv.appendChild(contentDiv);
    mcpChatContainer.appendChild(msgDiv);
    scrollMcpToBottom();
    return msgDiv;
}

function appendMcpLoadingMessage() {
    const id = 'mcp-loading-' + Date.now();
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message bot-message';
    msgDiv.id = id;

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.innerHTML = '<span class="loading-dots">Thinking</span>';

    msgDiv.appendChild(contentDiv);
    mcpChatContainer.appendChild(msgDiv);
    scrollMcpToBottom();
    return id;
}

function removeMcpMessage(id) {
    const element = document.getElementById(id);
    if (element) {
        element.remove();
    }
}

function appendMcpToolResponse(data) {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message bot-message';

    // Type badge
    const badgeDiv = document.createElement('div');
    badgeDiv.className = 'response-type-badge mcp-tool-badge';
    badgeDiv.innerHTML = `<span class="badge-icon">🔧</span> MCP Tool: <strong>${data.tool_used}</strong>`;
    msgDiv.appendChild(badgeDiv);

    // If there's data from the tool, show it as a table
    if (data.tool_result && data.tool_result.data && data.tool_result.data.length > 0) {
        const tableContainer = document.createElement('div');
        tableContainer.className = 'data-table-container mcp-data-table';

        const table = document.createElement('table');
        const thead = document.createElement('thead');
        const tbody = document.createElement('tbody');

        // Header
        const headers = Object.keys(data.tool_result.data[0]);
        const trHead = document.createElement('tr');
        headers.forEach(h => {
            const th = document.createElement('th');
            th.textContent = h.charAt(0).toUpperCase() + h.slice(1);
            trHead.appendChild(th);
        });
        thead.appendChild(trHead);

        // Body (limit to 10 rows for display)
        const displayData = data.tool_result.data.slice(0, 10);
        displayData.forEach(row => {
            const tr = document.createElement('tr');
            headers.forEach(h => {
                const td = document.createElement('td');
                td.textContent = row[h] !== null ? row[h] : 'NULL';
                tr.appendChild(td);
            });
            tbody.appendChild(tr);
        });

        table.appendChild(thead);
        table.appendChild(tbody);
        tableContainer.appendChild(table);

        if (data.tool_result.data.length > 10) {
            const moreDiv = document.createElement('div');
            moreDiv.className = 'more-rows-notice';
            moreDiv.textContent = `... and ${data.tool_result.data.length - 10} more rows`;
            tableContainer.appendChild(moreDiv);
        }

        msgDiv.appendChild(tableContainer);
    }

    // Show SQL if available
    if (data.tool_result && data.tool_result.sql) {
        const sqlBlock = document.createElement('div');
        sqlBlock.className = 'sql-block';

        const label = document.createElement('div');
        label.className = 'sql-label';
        label.textContent = 'Generated SQL';

        const code = document.createElement('code');
        code.textContent = data.tool_result.sql;

        sqlBlock.appendChild(label);
        sqlBlock.appendChild(code);
        msgDiv.appendChild(sqlBlock);
    }

    // AI Response text
    if (data.response) {
        const responseDiv = document.createElement('div');
        responseDiv.className = 'message-content mcp-response-text';
        responseDiv.textContent = data.response;
        msgDiv.appendChild(responseDiv);
    }

    mcpChatContainer.appendChild(msgDiv);
    scrollMcpToBottom();
}

function appendMcpDirectResponse(text) {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message bot-message';

    // Type badge
    const badgeDiv = document.createElement('div');
    badgeDiv.className = 'response-type-badge direct-badge';
    badgeDiv.innerHTML = '<span class="badge-icon">💬</span> Direct Response';
    msgDiv.appendChild(badgeDiv);

    // Response text
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.textContent = text;
    msgDiv.appendChild(contentDiv);

    mcpChatContainer.appendChild(msgDiv);
    scrollMcpToBottom();
}

function scrollMcpToBottom() {
    mcpChatContainer.scrollTop = mcpChatContainer.scrollHeight;
}
