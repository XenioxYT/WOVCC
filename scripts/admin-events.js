(function () {
    'use strict';
    // Use server-injected config if available, fallback to hostname detection
    const API_BASE = window.APP_CONFIG ? window.APP_CONFIG.apiBase : (
        window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
            ? 'http://localhost:5000/api'
            : `${window.location.origin}/api`
    );
    let allEvents = [];
    let currentEditingEvent = null;
    let selectedImage = null;
    let imagePreviewUrl = null;
    // Initialize via explicit wiring from admin-page.js / SPA transitions.
    // No inline handlers; use delegated bindings instead.
    async function loadAdminEvents() {
        // Scroll to top immediately when loading admin events
        window.scrollTo(0, 0);

        console.log('loadAdminEvents called');
        try {
            showEventsLoading();
            console.log('Fetching events from/events?show_all=true&filter=all');
            const response = await window.WOVCCAuth.authenticatedFetch(`/events?show_all=true&filter=all`);
            const data = await response.json();
            console.log('Events data received:', data);
            if (data.success) {
                allEvents = data.events;
                console.log('Rendering', allEvents.length, 'events');
                renderAdminEventsList(allEvents);
            } else {
                console.error('API returned success:false', data);
                showEventsError('Failed to load events');
            }
        } catch (error) {
            console.error('Failed to load events:', error);
            showEventsError(error.message);
        }
    }

    function renderAdminEventsList(events) {
        console.log('renderAdminEventsList called with', events?.length, 'events');
        const container = document.getElementById('admin-events-list');
        console.log('Container element:', container);
        if (!container) {
            console.error('admin-events-list container not found!');
            return;
        }
        if (!events || events.length === 0) {
            console.log('No events to display');
            container.innerHTML = `<div style="text-align:center;padding:40px;color:var(--text-light);"><p>No events yet. Create your first event!</p></div>`;
            return;
        }

        const now = new Date();

        // Separate events into categories:
        // 1. Recurring parents (is_recurring=true && parent_event_id=null)
        // 2. Regular events (not recurring and not a child)
        // 3. Child events (parent_event_id != null) - grouped by parent

        const recurringParents = [];
        const childEventsByParent = {};
        const regularEvents = [];

        events.forEach(evt => {
            if (evt.parent_event_id) {
                // This is a child instance of a recurring event
                if (!childEventsByParent[evt.parent_event_id]) {
                    childEventsByParent[evt.parent_event_id] = [];
                }
                childEventsByParent[evt.parent_event_id].push(evt);
            } else if (evt.is_recurring) {
                // This is a parent recurring event
                recurringParents.push(evt);
            } else {
                // Regular standalone event
                regularEvents.push(evt);
            }
        });

        // Sort child events by date for each parent
        Object.values(childEventsByParent).forEach(children => {
            children.sort((a, b) => new Date(a.date) - new Date(b.date));
        });

        // Sort recurring parents by next occurrence (their own date)
        recurringParents.sort((a, b) => new Date(a.date) - new Date(b.date));

        // Split regular events into upcoming vs completed
        const upcoming = [];
        const completed = [];

        regularEvents.forEach(evt => {
            const d = new Date(evt.date);
            if (!isNaN(d.getTime()) && d < now) {
                completed.push(evt);
            } else {
                upcoming.push(evt);
            }
        });

        // Default sort within each panel:
        // - upcoming: soonest first
        // - completed: most recent first
        upcoming.sort((a, b) => new Date(a.date) - new Date(b.date));
        completed.sort((a, b) => new Date(b.date) - new Date(a.date));

        // Helper to build recurring parent card with expandable instances
        function buildRecurringParentCard(parent, children) {
            const escapeHtml = window.HTMLSanitizer ? window.HTMLSanitizer.escapeHtml : (str => String(str));

            const parentDate = new Date(parent.date);
            const startDateDisplay = parentDate.toLocaleDateString('en-GB', {
                day: 'numeric', month: 'short', year: 'numeric'
            });

            // Calculate date range from children
            let endDateDisplay = 'Ongoing';
            if (children && children.length > 0) {
                const lastChild = children[children.length - 1];
                const endDate = new Date(lastChild.date);
                endDateDisplay = endDate.toLocaleDateString('en-GB', {
                    day: 'numeric', month: 'short', year: 'numeric'
                });
            } else if (parent.recurrence_end_date) {
                const endDate = new Date(parent.recurrence_end_date);
                endDateDisplay = endDate.toLocaleDateString('en-GB', {
                    day: 'numeric', month: 'short', year: 'numeric'
                });
            }

            const instanceCount = 1 + (children ? children.length : 0);
            const patternLabel = (parent.recurrence_pattern || 'weekly').charAt(0).toUpperCase() +
                (parent.recurrence_pattern || 'weekly').slice(1);

            const statusBadge = parent.is_published
                ? '<span style="background:#d4edda;color:#155724;padding:4px 10px;border-radius:12px;font-size:0.75rem;font-weight:600;">Published</span>'
                : '<span style="background:#fff3cd;color:#856404;padding:4px 10px;border-radius:12px;font-size:0.75rem;font-weight:600;">Draft</span>';

            const safeTitle = escapeHtml(parent.title);
            const safeCategory = escapeHtml(parent.category || 'Uncategorized');
            const safeParentId = parseInt(parent.id, 10);

            // Build children rows for the expandable section
            let childrenHtml = '';
            if (children && children.length > 0) {
                childrenHtml = children.map(child => {
                    const childDate = new Date(child.date);
                    const childDateDisplay = childDate.toLocaleDateString('en-GB', {
                        day: 'numeric', month: 'short', year: 'numeric'
                    });
                    const isPast = childDate < now;
                    const childStatus = child.is_published
                        ? (isPast ? '<span style="color:#6c757d;">✓ Published (Past)</span>' : '<span style="color:#155724;">✓ Published</span>')
                        : '<span style="color:#856404;">Draft</span>';
                    const safeChildId = parseInt(child.id, 10);

                    return `
                        <tr style="border-bottom:1px solid var(--border-color);background:${isPast ? '#fafafa' : 'white'};">
                            <td style="padding:10px 12px;padding-left:40px;">
                                <span style="color:var(--text-light);font-size:0.85rem;">↳</span>
                                ${childDateDisplay}
                            </td>
                            <td style="padding:10px 12px;font-size:0.9rem;">${childStatus}</td>
                            <td style="padding:10px 12px;text-align:center;">
                                <button id="view-interested-${safeChildId}" style="background:none;border:none;color:var(--primary-color);cursor:pointer;font-weight:600;">${parseInt(child.interested_count, 10) || 0}</button>
                            </td>
                            <td style="padding:10px 12px;text-align:center;">
                                <div style="display:flex;gap:8px;justify-content:center;">
                                    <button id="edit-event-${safeChildId}" class="btn-icon" title="Edit Instance" style="width:28px;height:28px;">
                                        <svg fill="currentColor" viewBox="0 0 20 20" style="width:14px;height:14px;"><path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z"/></svg>
                                    </button>
                                    <button id="delete-event-${safeChildId}" class="btn-icon btn-icon-danger" title="Delete Instance" style="width:28px;height:28px;">
                                        <svg fill="currentColor" viewBox="0 0 20 20" style="width:14px;height:14px;"><path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd"/></svg>
                                    </button>
                                </div>
                            </td>
                        </tr>
                    `;
                }).join('');
            }

            return `
                <div style="border:1px solid var(--border-color);border-radius:8px;margin-bottom:12px;overflow:hidden;background:white;">
                    <!-- Parent Header (clickable to expand) -->
                    <div class="recurring-parent-header" data-parent-id="${safeParentId}" 
                         style="padding:16px;display:flex;align-items:center;gap:16px;cursor:pointer;background:linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);border-bottom:1px solid var(--border-color);">
                        <div style="display:flex;align-items:center;gap:8px;min-width:24px;">
                            <svg class="expand-icon" style="width:20px;height:20px;color:var(--primary-color);transition:transform 0.2s;" fill="currentColor" viewBox="0 0 20 20">
                                <path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clip-rule="evenodd"/>
                            </svg>
                        </div>
                        <div style="flex:1;">
                            <div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;">
                                <span style="font-weight:600;color:var(--text-dark);font-size:1rem;">${safeTitle}</span>
                                <span style="background:linear-gradient(135deg, var(--primary-color) 0%, #2d7a7a 100%);color:white;padding:3px 10px;border-radius:12px;font-size:0.75rem;font-weight:600;">
                                    🔄 ${patternLabel}
                                </span>
                                ${statusBadge}
                            </div>
                            <div style="font-size:0.85rem;color:var(--text-light);">
                                <span style="margin-right:16px;">📅 ${startDateDisplay} → ${endDateDisplay}</span>
                                <span style="margin-right:16px;">📊 ${instanceCount} instance${instanceCount !== 1 ? 's' : ''}</span>
                                <span>🏷️ ${safeCategory}</span>
                            </div>
                        </div>
                        <div style="display:flex;gap:10px;">
                            <button id="edit-event-${safeParentId}" class="btn-icon" title="Edit Master (updates all instances)" style="width:32px;height:32px;">
                                <svg fill="currentColor" viewBox="0 0 20 20" style="width:16px;height:16px;"><path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z"/></svg>
                            </button>
                            <button id="delete-event-${safeParentId}" class="btn-icon btn-icon-danger" title="Delete All Instances" style="width:32px;height:32px;">
                                <svg fill="currentColor" viewBox="0 0 20 20" style="width:16px;height:16px;"><path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd"/></svg>
                            </button>
                        </div>
                    </div>
                    <!-- Expandable Instances Table -->
                    <div class="recurring-instances" data-parent-id="${safeParentId}" style="display:none;">
                        <table style="width:100%;border-collapse:collapse;">
                            <thead>
                                <tr style="background:#f8f9fa;border-bottom:1px solid var(--border-color);">
                                    <th style="padding:10px 12px;text-align:left;font-weight:600;font-size:0.85rem;color:var(--text-light);">Date</th>
                                    <th style="padding:10px 12px;text-align:left;font-weight:600;font-size:0.85rem;color:var(--text-light);">Status</th>
                                    <th style="padding:10px 12px;text-align:center;font-weight:600;font-size:0.85rem;color:var(--text-light);">Interested</th>
                                    <th style="padding:10px 12px;text-align:center;font-weight:600;font-size:0.85rem;color:var(--text-light);">Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                <!-- Parent event as first row -->
                                <tr style="border-bottom:1px solid var(--border-color);background:#e7f3ff;">
                                    <td style="padding:10px 12px;font-weight:600;">
                                        ${startDateDisplay}
                                        <span style="font-size:0.75rem;color:var(--primary-color);margin-left:6px;">(Master)</span>
                                    </td>
                                    <td style="padding:10px 12px;font-size:0.9rem;">${parent.is_published ? '<span style="color:#155724;">✓ Published</span>' : '<span style="color:#856404;">Draft</span>'}</td>
                                    <td style="padding:10px 12px;text-align:center;">
                                        <button id="view-interested-${safeParentId}" style="background:none;border:none;color:var(--primary-color);cursor:pointer;font-weight:600;">${parseInt(parent.interested_count, 10) || 0}</button>
                                    </td>
                                    <td style="padding:10px 12px;text-align:center;font-size:0.85rem;color:var(--text-light);">
                                        Use header buttons
                                    </td>
                                </tr>
                                ${childrenHtml}
                            </tbody>
                        </table>
                    </div>
                </div>
            `;
        }

        // Helper to build a sortable table HTML fragment for regular events
        function buildTableHtml(list, tableIdPrefix) {
            if (!list.length) {
                return `<div style="text-align:center;padding:16px;color:var(--text-light);font-size:0.9rem;">No events in this section.</div>`;
            }

            return `
              <div style="overflow-x:auto;">
                <table id="${tableIdPrefix}-table" style="width:100%;border-collapse:collapse;">
                  <thead>
                    <tr style="background:var(--secondary-bg);border-bottom:2px solid var(--border-color);">
                      <th style="padding:12px;text-align:left;font-weight:600;cursor:pointer;white-space:nowrap;"
                          data-sort-key="title">
                        <span class="sort-label" data-label="Title">Title</span>
                      </th>
                      <th style="padding:12px;text-align:left;font-weight:600;cursor:pointer;white-space:nowrap;"
                          data-sort-key="date">
                        <span class="sort-label" data-label="Date">Date</span>
                      </th>
                      <th style="padding:12px;text-align:left;font-weight:600;cursor:pointer;"
                          data-sort-key="category">
                        <span class="sort-label" data-label="Category">Category</span>
                      </th>
                      <th style="padding:12px;text-align:center;font-weight:600;cursor:pointer;white-space:nowrap;"
                          data-sort-key="interested">
                        <span class="sort-label" data-label="Interested">Interested</span>
                      </th>
                      <th style="padding:12px;text-align:center;font-weight:600;cursor:pointer;white-space:nowrap;"
                          data-sort-key="status">
                        <span class="sort-label" data-label="Status">Status</span>
                      </th>
                      <th style="padding:12px;text-align:center;font-weight:600;">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    ${list.map(event => createEventRow(event)).join('')}
                  </tbody>
                </table>
              </div>`;
        }

        // Render all three sections
        const recurringCount = recurringParents.length;
        const totalRecurringInstances = recurringParents.reduce((sum, p) => sum + 1 + (childEventsByParent[p.id]?.length || 0), 0);

        container.innerHTML = `
          <div style="display:flex;flex-direction:column;gap:24px;">

            ${recurringCount > 0 ? `
            <div style="border:1px solid var(--border-color);border-radius:8px;padding:16px;background:linear-gradient(135deg, #f0f7f7 0%, #e8f4f4 100%);">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
                <h4 style="margin:0;font-size:1rem;color:var(--primary-color);display:flex;align-items:center;gap:8px;">
                  <svg style="width:20px;height:20px;" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd"/></svg>
                  Recurring Events
                </h4>
                <span style="font-size:0.85rem;color:var(--text-light);">
                  ${recurringCount} series • ${totalRecurringInstances} total instances
                </span>
              </div>
              <div id="recurring-events-container">
                ${recurringParents.map(parent => buildRecurringParentCard(parent, childEventsByParent[parent.id] || [])).join('')}
              </div>
            </div>
            ` : ''}

            <div style="border:1px solid var(--border-color);border-radius:8px;padding:16px;background:#ffffff;">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
                <h4 style="margin:0;font-size:1rem;color:var(--primary-color);">
                  Upcoming & Active Events
                </h4>
                <span style="font-size:0.85rem;color:var(--text-light);">
                  Sorted by nearest first • ${upcoming.length} event${upcoming.length !== 1 ? 's' : ''}
                </span>
              </div>
              ${buildTableHtml(upcoming, 'upcoming-events')}
            </div>

            <div style="border:1px solid var(--border-color);border-radius:8px;padding:16px;background:#fafafa;">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
                <h4 style="margin:0;font-size:1rem;color:var(--text-dark);">
                  Completed / Past Events
                </h4>
                <span style="font-size:0.85rem;color:var(--text-light);">
                  Sorted by most recent first • ${completed.length} event${completed.length !== 1 ? 's' : ''}
                </span>
              </div>
              ${buildTableHtml(completed, 'completed-events')}
            </div>

          </div>
        `;

        // Wire up expand/collapse for recurring events
        container.querySelectorAll('.recurring-parent-header').forEach(header => {
            header.addEventListener('click', (e) => {
                // Don't toggle if clicking on action buttons
                if (e.target.closest('.btn-icon')) return;

                const parentId = header.dataset.parentId;
                const instancesContainer = container.querySelector(`.recurring-instances[data-parent-id="${parentId}"]`);
                const expandIcon = header.querySelector('.expand-icon');

                if (instancesContainer) {
                    const isExpanded = instancesContainer.style.display !== 'none';
                    instancesContainer.style.display = isExpanded ? 'none' : 'block';
                    if (expandIcon) {
                        expandIcon.style.transform = isExpanded ? '' : 'rotate(90deg)';
                    }
                }
            });
        });

        // Wire up all row actions for all events
        function bindRowActions(list) {
            list.forEach(event => {
                document.getElementById(`edit-event-${event.id}`)?.addEventListener('click', () => openEditEventModal(event));
                document.getElementById(`delete-event-${event.id}`)?.addEventListener('click', () => deleteEvent(event.id));
                document.getElementById(`view-interested-${event.id}`)?.addEventListener('click', () => viewInterestedUsers(event.id));
            });
        }

        // Bind actions for all event types
        bindRowActions(upcoming);
        bindRowActions(completed);
        bindRowActions(recurringParents);
        // Bind actions for all child events
        Object.values(childEventsByParent).forEach(children => bindRowActions(children));

        // Enable independent sorting for each table section
        function enableTableSorting(sourceList, tableIdPrefix, defaultSortKey, defaultDirection) {
            const table = container.querySelector(`#${tableIdPrefix}-table`);
            if (!table) return;

            const thead = table.querySelector('thead');
            const tbody = table.querySelector('tbody');
            if (!thead || !tbody) return;

            let currentSort = {
                key: defaultSortKey || 'date',
                direction: defaultDirection || 'asc'
            };

            function updateSortIndicators() {
                thead.querySelectorAll('th[data-sort-key]').forEach(thEl => {
                    const key = thEl.getAttribute('data-sort-key');
                    const labelSpan = thEl.querySelector('.sort-label');
                    if (!key || !labelSpan) return;

                    const base = labelSpan.getAttribute('data-label') || '';

                    if (key === currentSort.key) {
                        const arrow = currentSort.direction === 'asc' ? ' ▲' : ' ▼';
                        labelSpan.textContent = base + arrow;
                    } else {
                        labelSpan.textContent = base;
                    }
                });
            }

            function sortAndRender() {
                const sorted = [...sourceList].sort((a, b) => {
                    switch (currentSort.key) {
                        case 'title':
                            return compareStrings(a.title, b.title, currentSort.direction);
                        case 'date':
                            return compareDates(a.date, b.date, currentSort.direction);
                        case 'category':
                            return compareStrings(a.category || '', b.category || '', currentSort.direction);
                        case 'interested': {
                            const av = a.interested_count || 0;
                            const bv = b.interested_count || 0;
                            return currentSort.direction === 'asc' ? av - bv : bv - av;
                        }
                        case 'status': {
                            const av = a.is_published ? 1 : 0;
                            const bv = b.is_published ? 1 : 0;
                            return currentSort.direction === 'asc' ? av - bv : bv - av;
                        }
                        default:
                            return 0;
                    }
                });

                tbody.innerHTML = sorted.map(ev => createEventRow(ev)).join('');
                sorted.forEach(ev => {
                    document.getElementById(`edit-event-${ev.id}`)?.addEventListener('click', () => openEditEventModal(ev));
                    document.getElementById(`delete-event-${ev.id}`)?.addEventListener('click', () => deleteEvent(ev.id));
                    document.getElementById(`view-interested-${ev.id}`)?.addEventListener('click', () => viewInterestedUsers(ev.id));
                });

                updateSortIndicators();
            }

            thead.querySelectorAll('th[data-sort-key]').forEach(th => {
                th.addEventListener('click', () => {
                    const key = th.getAttribute('data-sort-key');
                    if (!key) return;

                    if (currentSort.key === key) {
                        currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
                    } else {
                        currentSort.key = key;
                        currentSort.direction = 'asc';
                    }

                    sortAndRender();
                });
            });

            // Initial indicators + ensure default sorted order is reflected
            updateSortIndicators();
            sortAndRender();
        }

        // Upcoming: default nearest first (asc)
        enableTableSorting(upcoming, 'upcoming-events', 'date', 'asc');
        // Completed: default most recent first (desc)
        enableTableSorting(completed, 'completed-events', 'date', 'desc');
    }

    function compareStrings(a, b, direction) {
        const res = String(a).localeCompare(String(b), 'en', { sensitivity: 'base' });
        return direction === 'asc' ? res : -res;
    }

    function compareDates(a, b, direction) {
        const da = new Date(a);
        const db = new Date(b);
        const diff = da - db;
        if (diff === 0) return 0;
        return direction === 'asc' ? (diff < 0 ? -1 : 1) : (diff < 0 ? 1 : -1);
    }

    function createEventRow(event) {
        // Security: Use escapeHtml to prevent XSS attacks
        const escapeHtml = window.HTMLSanitizer ? window.HTMLSanitizer.escapeHtml : (str => String(str));

        const eventDate = new Date(event.date);
        const dateDisplay = eventDate.toLocaleDateString('en-GB', {
            day: 'numeric',
            month: 'short',
            year: 'numeric'
        });
        const statusBadge = event.is_published ? '<span style="background:#d4edda;color:#155724;padding:4px 10px;border-radius:12px;font-size:0.85rem;font-weight:600;">Published</span>' : '<span style="background:#fff3cd;color:#856404;padding:4px 10px;border-radius:12px;font-size:0.85rem;font-weight:600;">Draft</span>';

        // Escape all user-provided data
        const safeTitle = escapeHtml(event.title);
        const safeDescription = escapeHtml(event.short_description);
        const safeCategory = escapeHtml(event.category || '-');
        const safeEventId = parseInt(event.id, 10);
        const truncatedDesc = safeDescription.substring(0, 60) + (safeDescription.length > 60 ? '...' : '');

        return `<tr style="border-bottom:1px solid var(--border-color);"><td style="padding:12px;"><div style="font-weight:600;color:var(--text-dark);margin-bottom:4px;">${safeTitle}</div><div style="font-size:0.85rem;color:var(--text-light);">${truncatedDesc}</div></td><td style="padding:12px;white-space:nowrap;">${dateDisplay}</td><td style="padding:12px;">${safeCategory}</td><td style="padding:12px;text-align:center;"><button id="view-interested-${safeEventId}" style="background:none;border:none;color:var(--primary-color);cursor:pointer;font-weight:600;text-decoration:underline;">${parseInt(event.interested_count, 10) || 0}</button></td><td style="padding:12px;text-align:center;">${statusBadge}</td><td style="padding:12px;text-align:center;"><div style="display:flex;gap:10px;justify-content:center;"><button id="edit-event-${safeEventId}" class="btn-icon" title="Edit"><svg fill="currentColor" viewBox="0 0 20 20"><path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z"/></svg></button><button id="delete-event-${safeEventId}" class="btn-icon btn-icon-danger" title="Delete"><svg fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd"/></svg></button></div></td></tr>`;
    }

    function showEventsLoading() {
        const container = document.getElementById('admin-events-list');
        if (!container) return;
        container.innerHTML = `<div style="text-align:center;padding:40px;"><div class="skeleton-spinner"></div><p style="margin-top:15px;color:var(--text-light);">Loading events...</p></div>`;
    }

    function showEventsError(message) {
        const container = document.getElementById('admin-events-list');
        if (!container) return;
        container.innerHTML = `<div style="text-align:center;padding:40px;color:var(--accent-color);"><p>${message}</p></div>`;
    }

    function openCreateEventModal() {
        currentEditingEvent = null;
        selectedImage = null;
        imagePreviewUrl = null;
        const modal = document.getElementById('event-modal');
        if (!modal) return;
        document.getElementById('event-form').reset();
        document.getElementById('event-modal-title').textContent = 'Create New Event';
        document.getElementById('event-submit-btn').textContent = 'Create Event';
        document.getElementById('image-preview-container').style.display = 'none';
        document.getElementById('recurring-options').style.display = 'none';

        // Reset football match section
        const footballOptions = document.getElementById('football-match-options');
        const footballNote = document.getElementById('football-image-note');
        if (footballOptions) footballOptions.style.display = 'none';
        if (footballNote) footballNote.style.display = 'none';
        document.getElementById('home-team-status').textContent = '';
        document.getElementById('away-team-status').textContent = '';

        // Reset markdown preview
        const preview = document.getElementById('markdown-preview');
        const btn = document.getElementById('markdown-preview-btn');
        preview.innerHTML = '';
        preview.style.display = 'none';
        btn.textContent = 'Preview';

        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }

    function openEditEventModal(event) {
        currentEditingEvent = event;
        selectedImage = null;
        imagePreviewUrl = event.image_url;
        const modal = document.getElementById('event-modal');
        if (!modal) return;
        document.getElementById('event-title').value = event.title;
        document.getElementById('event-short-description').value = event.short_description;
        document.getElementById('event-long-description').value = event.long_description;

        // Set date only (not time) - date field expects YYYY-MM-DD format
        document.getElementById('event-date').value = new Date(event.date).toISOString().slice(0, 10);

        // Set time if available
        document.getElementById('event-time').value = event.time || '';

        document.getElementById('event-location').value = event.location || '';
        document.getElementById('event-category').value = event.category || '';
        document.getElementById('event-is-recurring').checked = event.is_recurring || false;
        document.getElementById('event-recurrence-pattern').value = event.recurrence_pattern || 'weekly';
        document.getElementById('event-recurrence-end-date').value = event.recurrence_end_date ? new Date(event.recurrence_end_date).toISOString().slice(0, 10) : '';
        document.getElementById('event-is-published').checked = event.is_published || false;

        // Football match fields
        document.getElementById('event-is-football-match').checked = event.is_football_match || false;
        document.getElementById('event-home-team').value = event.home_team || '';
        document.getElementById('event-away-team').value = event.away_team || '';
        document.getElementById('event-football-competition').value = event.football_competition || '';

        const footballOptions = document.getElementById('football-match-options');
        const footballNote = document.getElementById('football-image-note');
        if (event.is_football_match) {
            if (footballOptions) footballOptions.style.display = 'block';
            if (footballNote) footballNote.style.display = 'block';
        } else {
            if (footballOptions) footballOptions.style.display = 'none';
            if (footballNote) footballNote.style.display = 'none';
        }
        document.getElementById('home-team-status').textContent = '';
        document.getElementById('away-team-status').textContent = '';

        if (imagePreviewUrl) {
            document.getElementById('image-preview').src = imagePreviewUrl;
            document.getElementById('image-preview-container').style.display = 'block';
        } else {
            document.getElementById('image-preview-container').style.display = 'none';
        }
        document.getElementById('recurring-options').style.display = event.is_recurring ? 'block' : 'none';

        // Hide markdown preview on edit
        const preview = document.getElementById('markdown-preview');
        const btn = document.getElementById('markdown-preview-btn');
        preview.style.display = 'none';
        btn.textContent = 'Preview';

        document.getElementById('event-modal-title').textContent = 'Edit Event';
        document.getElementById('event-submit-btn').textContent = 'Update Event';
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }

    function closeEventModal() {
        const modal = document.getElementById('event-modal');
        if (modal) {
            modal.style.display = 'none';
        }
        document.body.style.overflow = '';
        currentEditingEvent = null;
        selectedImage = null;
        imagePreviewUrl = null;
    }
    async function handleEventSubmit(e) {
        e.preventDefault();

        // Validate recurring event if enabled
        const isRecurring = document.getElementById('event-is-recurring').checked;
        if (isRecurring) {
            const endDate = document.getElementById('event-recurrence-end-date').value;
            const startDate = document.getElementById('event-date').value;

            if (!endDate) {
                if (typeof showNotification === 'function') {
                    showNotification('Please select an end date for the recurring event', 'error');
                }
                return;
            }

            if (new Date(endDate) <= new Date(startDate)) {
                if (typeof showNotification === 'function') {
                    showNotification('Recurrence end date must be after the start date', 'error');
                }
                return;
            }
        }

        const formData = new FormData();
        formData.append('title', document.getElementById('event-title').value);
        formData.append('short_description', document.getElementById('event-short-description').value);
        formData.append('long_description', document.getElementById('event-long-description').value);

        // Send date and time separately
        formData.append('date', document.getElementById('event-date').value);
        formData.append('time', document.getElementById('event-time').value);

        formData.append('location', document.getElementById('event-location').value);
        formData.append('category', document.getElementById('event-category').value);

        // Football match fields
        const isFootballMatch = document.getElementById('event-is-football-match').checked;
        formData.append('is_football_match', isFootballMatch);
        if (isFootballMatch) {
            formData.append('home_team', document.getElementById('event-home-team').value);
            formData.append('away_team', document.getElementById('event-away-team').value);
            formData.append('football_competition', document.getElementById('event-football-competition').value);
        }

        formData.append('is_recurring', isRecurring);
        formData.append('recurrence_pattern', document.getElementById('event-recurrence-pattern').value);
        formData.append('recurrence_end_date', document.getElementById('event-recurrence-end-date').value);
        formData.append('is_published', document.getElementById('event-is-published').checked);
        if (selectedImage) {
            formData.append('image', selectedImage);
        }

        const submitBtn = document.getElementById('event-submit-btn');
        const originalBtnText = submitBtn.textContent;
        submitBtn.disabled = true;
        submitBtn.textContent = currentEditingEvent ? 'Updating...' : 'Creating...';

        try {
            const url = currentEditingEvent ? `${API_BASE}/events/${currentEditingEvent.id}` : `${API_BASE}/events`;
            const method = currentEditingEvent ? 'PUT' : 'POST';
            // Use WOVCCAuth for authenticated requests
            const token = window.WOVCCAuth && window.WOVCCAuth.isLoggedIn()
                ? (sessionStorage.getItem('wovcc_access_token') || localStorage.getItem('wovcc_access_token'))
                : null;

            if (!token) {
                throw new Error('Authentication required');
            }

            const response = await fetch(url, {
                method,
                headers: {
                    'Authorization': `Bearer ${token}`
                },
                body: formData
            });
            const data = await response.json();
            if (data.success) {
                if (typeof showNotification === 'function') {
                    showNotification(data.message, 'success');
                }
                closeEventModal();
                loadAdminEvents();
            } else {
                if (typeof showNotification === 'function') {
                    showNotification(data.error || 'Failed to save event', 'error');
                }
            }
        } catch (error) {
            console.error('Failed to save event:', error);
            if (typeof showNotification === 'function') {
                showNotification('Failed to save event', 'error');
            }
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.textContent = originalBtnText;
            }
        }
    }
    async function deleteEvent(eventId) {
        // Use mobile-friendly modal instead of blocking confirm
        const confirmed = await window.WOVCCModal.confirm({
            title: 'Delete Event?',
            message: 'Are you sure you want to delete this event? This action cannot be undone.',
            type: 'danger',
            confirmText: 'Delete',
            cancelText: 'Cancel',
            dangerous: true
        });

        if (!confirmed) {
            return;
        }
        try {
            const response = await window.WOVCCAuth.authenticatedFetch(`/events/${eventId}`, {
                method: 'DELETE'
            });
            const data = await response.json();
            if (data.success) {
                if (typeof showNotification === 'function') {
                    showNotification('Event deleted successfully', 'success');
                }
                loadAdminEvents();
            } else {
                if (typeof showNotification === 'function') {
                    showNotification(data.error || 'Failed to delete event', 'error');
                }
            }
        } catch (error) {
            console.error('Failed to delete event:', error);
            if (typeof showNotification === 'function') {
                showNotification('Failed to delete event', 'error');
            }
        }
    }
    async function viewInterestedUsers(eventId) {
        try {
            const response = await window.WOVCCAuth.authenticatedFetch(`/events/${eventId}/interested-users`);
            const data = await response.json();
            if (data.success) {
                showInterestedUsersModal(data.users, data.count);
            } else {
                if (typeof showNotification === 'function') {
                    showNotification('Failed to load interested users', 'error');
                }
            }
        } catch (error) {
            console.error('Failed to load interested users:', error);
            if (typeof showNotification === 'function') {
                showNotification('Failed to load interested users', 'error');
            }
        }
    }

    function showInterestedUsersModal(users, count) {
        // Security: Use escapeHtml to prevent XSS attacks
        const escapeHtml = window.HTMLSanitizer ? window.HTMLSanitizer.escapeHtml : (str => String(str));

        const modal = document.getElementById('interested-users-modal');
        if (!modal) return;
        const container = document.getElementById('interested-users-list');
        if (!users || users.length === 0) {
            container.innerHTML = `<p style="text-align:center;padding:20px;color:var(--text-light);">No one has shown interest yet.</p>`;
        } else {
            const safeCount = parseInt(count, 10);
            const userRows = users.map(user => {
                const safeName = escapeHtml(user.name);
                const safeEmail = escapeHtml(user.email);
                const memberBadge = user.is_member ? '<span style="font-size:0.75rem;background:var(--primary-color);color:white;padding:2px 6px;border-radius:4px;margin-left:6px;">Member</span>' : '';
                const safeDate = new Date(user.created_at).toLocaleDateString('en-GB');

                return `<div style="padding:12px;border-bottom:1px solid var(--border-color);display:flex;align-items:center;gap:10px;"><svg style="width:20px;height:20px;color:var(--primary-color);" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clip-rule="evenodd"/></svg><div style="flex:1;"><div style="font-weight:600;color:var(--text-dark);">${safeName}${memberBadge}</div><div style="font-size:0.9rem;color:var(--text-light);">${safeEmail}</div></div><div style="font-size:0.85rem;color:var(--text-light);">${safeDate}</div></div>`;
            }).join('');

            container.innerHTML = `<div style="margin-bottom:15px;color:var(--text-light);"><strong>${safeCount}</strong> ${safeCount === 1 ? 'person has' : 'people have'} shown interest in this event.</div><div style="max-height:400px;overflow-y:auto;">${userRows}</div>`;
        }
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }

    function closeInterestedUsersModal() {
        const modal = document.getElementById('interested-users-modal');
        if (modal) {
            modal.style.display = 'none';
        }
        document.body.style.overflow = '';
    }

    function handleImageSelect(e) {
        const file = e.target.files[0];
        if (!file) return;
        const validTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp'];
        if (!validTypes.includes(file.type)) {
            if (typeof showNotification === 'function') {
                showNotification('Invalid file type. Please select a PNG, JPG, or WebP image.', 'error');
            }
            return;
        }
        if (file.size > 5 * 1024 * 1024) {
            if (typeof showNotification === 'function') {
                showNotification('File too large. Maximum size is 5MB.', 'error');
            }
            return;
        }
        selectedImage = file;
        const reader = new FileReader();
        reader.onload = function (e) {
            imagePreviewUrl = e.target.result;
            document.getElementById('image-preview').src = imagePreviewUrl;
            document.getElementById('image-preview-container').style.display = 'block';
        };
        reader.readAsDataURL(file);
    }

    function removeImage() {
        selectedImage = null;
        imagePreviewUrl = null;
        document.getElementById('event-image').value = '';
        document.getElementById('image-preview-container').style.display = 'none';
    }

    function toggleRecurringOptions() {
        const isRecurring = document.getElementById('event-is-recurring').checked;
        document.getElementById('recurring-options').style.display = isRecurring ? 'block' : 'none';
    }

    function toggleFootballOptions() {
        const isFootball = document.getElementById('event-is-football-match').checked;
        const footballOptions = document.getElementById('football-match-options');
        const footballNote = document.getElementById('football-image-note');

        if (footballOptions) footballOptions.style.display = isFootball ? 'block' : 'none';
        if (footballNote) footballNote.style.display = isFootball ? 'block' : 'none';

        // Reset status messages
        document.getElementById('home-team-status').textContent = '';
        document.getElementById('away-team-status').textContent = '';
    }

    function toggleMarkdownPreview() {
        const longDescription = document.getElementById('event-long-description').value;
        const preview = document.getElementById('markdown-preview');
        const btn = document.getElementById('markdown-preview-btn');

        if (preview.style.display === 'none' || preview.style.display === '') {
            // Show preview
            if (typeof marked !== 'undefined') {
                preview.innerHTML = marked.parse(longDescription);
            } else {
                preview.innerHTML = longDescription.replace(/\n/g, '<br>');
            }
            preview.style.display = 'block';
            btn.textContent = 'Edit';
        } else {
            // Hide preview
            preview.style.display = 'none';
            btn.textContent = 'Preview';
        }
    }

    function handleRecurrencePatternChange() {
        const pattern = document.getElementById('event-recurrence-pattern').value;


        // Show info about the pattern
        if (typeof showNotification === 'function') {
            let message = '';
            switch (pattern) {
                case 'daily':
                    message = 'Event will repeat every day';
                    break;
                case 'weekly':
                    message = 'Event will repeat on the same day each week';
                    break;
                case 'monthly':
                    message = 'Event will repeat on the same date each month';
                    break;
            }
            showNotification(message, 'info');
        }
    }

    async function generateEventDescriptions() {
        try {
            const title = document.getElementById('event-title')?.value || '';
            const shortDescription = document.getElementById('event-short-description')?.value || '';
            const longDescription = document.getElementById('event-long-description')?.value || '';
            const dateValue = document.getElementById('event-date')?.value || '';
            const timeValue = document.getElementById('event-time')?.value || '';
            const locationValue = document.getElementById('event-location')?.value || '';
            const categoryValue = document.getElementById('event-category')?.value || '';
            const isRecurring = !!document.getElementById('event-is-recurring')?.checked;
            const recurrencePattern = document.getElementById('event-recurrence-pattern')?.value || '';
            const recurrenceEndDate = document.getElementById('event-recurrence-end-date')?.value || '';

            // Football match fields
            const isFootballMatch = !!document.getElementById('event-is-football-match')?.checked;
            const homeTeam = document.getElementById('event-home-team')?.value || '';
            const awayTeam = document.getElementById('event-away-team')?.value || '';
            const footballCompetition = document.getElementById('event-football-competition')?.value || '';

            if (!title || !dateValue) {
                if (typeof showNotification === 'function') {
                    showNotification('Please provide at least a title and date before generating descriptions.', 'error');
                }
                return;
            }

            const buttonShort = document.querySelector('[data-admin-events-action="ai-generate-short"]');
            const buttonLong = document.querySelector('[data-admin-events-action="ai-generate-long"]');
            const allButtons = [buttonShort, buttonLong].filter(Boolean);
            allButtons.forEach(btn => {
                btn.disabled = true;
                btn.dataset.originalText = btn.textContent;
                btn.textContent = 'Generating...';
            });

            const body = {
                title,
                short_description: shortDescription,
                long_description: longDescription,
                date: dateValue,
                time: timeValue || null,
                location: locationValue || null,
                category: categoryValue || null,
                is_recurring: isRecurring,
                recurrence_pattern: recurrencePattern || null,
                recurrence_end_date: recurrenceEndDate || null,
                is_football_match: isFootballMatch,
                home_team: isFootballMatch ? homeTeam : null,
                away_team: isFootballMatch ? awayTeam : null,
                football_competition: isFootballMatch ? footballCompetition : null
            };

            // Use WOVCCAuth for authenticated requests
            const token = window.WOVCCAuth && window.WOVCCAuth.isLoggedIn()
                ? (sessionStorage.getItem('wovcc_access_token') || localStorage.getItem('wovcc_access_token'))
                : null;

            const response = await fetch(`${API_BASE}/events/ai-descriptions`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(token ? { 'Authorization': `Bearer ${token}` } : {})
                },
                body: JSON.stringify(body)
            });

            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.error || 'Failed to generate descriptions');
            }

            // Expecting JSON: { short_description: "...", long_description: "..." }
            if (!data.result || typeof data.result !== 'object') {
                throw new Error('Unexpected AI response format');
            }

            const newShort = (data.result.short_description || '').trim();
            const newLong = (data.result.long_description || '').trim();

            if (newShort) {
                const shortEl = document.getElementById('event-short-description');
                if (shortEl) shortEl.value = newShort;
            }
            if (newLong) {
                const longEl = document.getElementById('event-long-description');
                if (longEl) longEl.value = newLong;
            }

            if (typeof showNotification === 'function') {
                showNotification('AI descriptions generated successfully.', 'success');
            }
        } catch (error) {
            console.error('Error generating AI descriptions', error);
            if (typeof showNotification === 'function') {
                showNotification(error.message || 'Failed to generate AI descriptions.', 'error');
            }
        } finally {
            const buttonShort = document.querySelector('[data-admin-events-action="ai-generate-short"]');
            const buttonLong = document.querySelector('[data-admin-events-action="ai-generate-long"]');
            const allButtons = [buttonShort, buttonLong].filter(Boolean);
            allButtons.forEach(btn => {
                btn.disabled = false;
                if (btn.dataset.originalText) {
                    btn.textContent = btn.dataset.originalText;
                    delete btn.dataset.originalText;
                }
            });
        }
    }

    // Public API (invoked from admin-page.js via data-* attributes)
    window.AdminEvents = {
        loadAdminEvents,
        openCreateEventModal,
        closeEventModal,
        handleEventSubmit,
        closeInterestedUsersModal,
        handleImageSelect,
        removeImage,
        toggleRecurringOptions,
        toggleFootballOptions,
        toggleMarkdownPreview,
        handleRecurrencePatternChange,
        generateEventDescriptions
    };

    // Delegated event listeners (no inline JS)
    document.addEventListener('click', function (e) {
        const target = e.target.closest('[data-admin-events-action]');
        if (!target) return;

        const action = target.getAttribute('data-admin-events-action');
        if (!action) return;

        if (action === 'open-create-modal') {
            e.preventDefault();
            openCreateEventModal();
        } else if (action === 'close-event-modal') {
            e.preventDefault();
            closeEventModal();
        } else if (action === 'close-interested-users-modal') {
            e.preventDefault();
            closeInterestedUsersModal();
        } else if (action === 'toggle-markdown-preview') {
            e.preventDefault();
            toggleMarkdownPreview();
        } else if (action === 'remove-image') {
            e.preventDefault();
            removeImage();
        } else if (action === 'ai-generate-short' || action === 'ai-generate-long') {
            e.preventDefault();
            // Single generator updates both fields based on current form context
            generateEventDescriptions();
        }
    });

    document.addEventListener('change', function (e) {
        const target = e.target;

        if (target.matches('[data-admin-events-file-input="image"]')) {
            handleImageSelect(e);
        }

        if (target.matches('[data-admin-events-action="toggle-recurring"]')) {
            toggleRecurringOptions();
        }

        if (target.matches('[data-admin-events-action="toggle-football"]')) {
            toggleFootballOptions();
        }

        if (target.matches('[data-admin-events-action="recurrence-pattern"]')) {
            handleRecurrencePatternChange();
        }
    });

    // Attach form submit handler
    document.addEventListener('submit', function (e) {
        if (e.target && e.target.id === 'event-form') {
            handleEventSubmit(e);
        }
    });
})();