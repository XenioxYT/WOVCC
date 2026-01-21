(function () {
        'use strict';

        // Admin Beer Images Management Module
        window.AdminBeerImages = window.AdminBeerImages || {};

        let allBeerImages = [];
        let currentEditingImage = null;
        let currentFilter = 'all';
        let currentSearch = '';

        // Load all beer images
        async function loadBeerImages() {
                try {
                        showLoadingState();

                        const params = new URLSearchParams({
                                filter: currentFilter,
                                search: currentSearch
                        });

                        const response = await window.WOVCCAuth.authenticatedFetch(`/beer-images/admin?${params}`);
                        const data = await response.json();

                        if (data.success) {
                                allBeerImages = data.beer_images || [];
                                renderImagesTable(allBeerImages);
                        } else {
                                showError('Failed to load beer images: ' + (data.error || 'Unknown error'));
                        }
                } catch (error) {
                        console.error('Error loading beer images:', error);
                        showError('Failed to load beer images');
                }
        }

        // Show loading state
        function showLoadingState() {
                const container = document.getElementById('admin-beer-images-list');
                if (!container) return;

                container.innerHTML = `
      <div style="text-align: center; padding: 40px;">
        <div class="skeleton-spinner"></div>
        <p style="margin-top: 15px; color: var(--text-light);">Loading beer images...</p>
      </div>
    `;
        }

        // Render the images table
        function renderImagesTable(images) {
                const container = document.getElementById('admin-beer-images-list');
                if (!container) return;

                if (!images || images.length === 0) {
                        container.innerHTML = `
        <div style="text-align: center; padding: 60px 20px; color: var(--text-light);">
          <svg style="width: 60px; height: 60px; margin-bottom: 15px; opacity: 0.5;" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clip-rule="evenodd"/>
          </svg>
          <h3 style="margin: 0 0 8px 0; font-weight: 600; color: var(--text-dark);">No Beer Images</h3>
          <p style="margin: 0;">Add your first beer image to display in the homepage carousel.</p>
        </div>
      `;
                        return;
                }

                const escapeHtml = window.HTMLSanitizer ? window.HTMLSanitizer.escapeHtml : (str => String(str));

                const rows = images.map(image => createImageRow(image, escapeHtml)).join('');

                container.innerHTML = `
      <div style="overflow-x: auto;">
        <table style="width: 100%; border-collapse: collapse; min-width: 600px;">
          <thead>
            <tr style="background: var(--secondary-bg); border-bottom: 2px solid var(--border-color);">
              <th style="padding: 14px 16px; text-align: left; font-weight: 600; color: var(--text-dark);">Image</th>
              <th style="padding: 14px 16px; text-align: left; font-weight: 600; color: var(--text-dark);">Name</th>
              <th style="padding: 14px 16px; text-align: center; font-weight: 600; color: var(--text-dark);">Order</th>
              <th style="padding: 14px 16px; text-align: center; font-weight: 600; color: var(--text-dark);">Status</th>
              <th style="padding: 14px 16px; text-align: center; font-weight: 600; color: var(--text-dark);">Actions</th>
            </tr>
          </thead>
          <tbody>
            ${rows}
          </tbody>
        </table>
      </div>
    `;

                attachImageEventListeners();
        }

        // Create a single image row
        function createImageRow(image, escapeHtml) {
                const safeName = escapeHtml(image.name);
                const safeId = parseInt(image.id, 10);
                const statusClass = image.is_active ? 'active' : 'inactive';
                const statusText = image.is_active ? 'Active' : 'Inactive';

                return `
      <tr style="border-bottom: 1px solid var(--border-color);">
        <td style="padding: 12px 16px;">
          <img src="${escapeHtml(image.image_url)}" alt="${safeName}" 
               style="width: 80px; height: 60px; object-fit: cover; border-radius: 6px; border: 1px solid var(--border-color);"
               loading="lazy">
        </td>
        <td style="padding: 12px 16px;">
          <span style="font-weight: 500; color: var(--text-dark);">${safeName}</span>
        </td>
        <td style="padding: 12px 16px; text-align: center;">
          <span style="font-weight: 600; color: var(--primary-color);">${image.display_order}</span>
        </td>
        <td style="padding: 12px 16px; text-align: center;">
          <span class="payment-status-badge ${statusClass}">${statusText}</span>
        </td>
        <td style="padding: 12px 16px; text-align: center;">
          <div style="display: flex; gap: 8px; justify-content: center;">
            <button class="btn-icon" data-admin-beer-images-action="edit" data-image-id="${safeId}" title="Edit">
              <svg fill="currentColor" viewBox="0 0 20 20">
                <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z"/>
              </svg>
            </button>
            <button class="btn-icon btn-icon-danger" data-admin-beer-images-action="delete" data-image-id="${safeId}" title="Delete">
              <svg fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd"/>
              </svg>
            </button>
          </div>
        </td>
      </tr>
    `;
        }

        // Attach event listeners
        function attachImageEventListeners() {
                // Search input
                const searchInput = document.getElementById('beer-images-search');
                if (searchInput) {
                        searchInput.addEventListener('input', debounce(function (e) {
                                currentSearch = e.target.value.trim();
                                loadBeerImages();
                        }, 300));
                }

                // Filter dropdown
                const filterSelect = document.getElementById('beer-images-filter');
                if (filterSelect) {
                        filterSelect.addEventListener('change', function (e) {
                                currentFilter = e.target.value;
                                loadBeerImages();
                        });
                }
        }

        // Delegated event listeners for buttons
        document.addEventListener('click', function (e) {
                const btn = e.target.closest('[data-admin-beer-images-action]');
                if (!btn) return;

                const action = btn.getAttribute('data-admin-beer-images-action');

                if (action === 'open-create-modal') {
                        e.preventDefault();
                        openCreateModal();
                } else if (action === 'close-modal') {
                        e.preventDefault();
                        closeModal();
                } else if (action === 'edit') {
                        e.preventDefault();
                        const imageId = parseInt(btn.getAttribute('data-image-id'), 10);
                        const image = allBeerImages.find(i => i.id === imageId);
                        if (image) {
                                openEditModal(image);
                        }
                } else if (action === 'delete') {
                        e.preventDefault();
                        const imageId = parseInt(btn.getAttribute('data-image-id'), 10);
                        const image = allBeerImages.find(i => i.id === imageId);
                        if (image) {
                                deleteImage(image);
                        }
                }
        });

        // Open create modal
        function openCreateModal() {
                currentEditingImage = null;

                document.getElementById('beer-image-modal-title').textContent = 'Add Beer Image';
                document.getElementById('beer-image-submit-btn').textContent = 'Add Image';
                document.getElementById('beer-image-form').reset();
                document.getElementById('beer-image-is-active').checked = true;

                // Hide preview
                document.getElementById('beer-image-preview-container').style.display = 'none';

                // Mark image as required for create
                document.getElementById('beer-image-file').required = true;

                document.getElementById('beer-image-modal').style.display = 'flex';
                document.body.style.overflow = 'hidden';
        }

        // Open edit modal
        function openEditModal(image) {
                currentEditingImage = image;

                document.getElementById('beer-image-modal-title').textContent = 'Edit Beer Image';
                document.getElementById('beer-image-submit-btn').textContent = 'Update Image';

                // Populate form
                document.getElementById('beer-image-name').value = image.name || '';
                document.getElementById('beer-image-order').value = image.display_order || 0;
                document.getElementById('beer-image-is-active').checked = image.is_active;

                // Show current image
                const previewImg = document.getElementById('beer-image-preview');
                previewImg.src = image.image_url;
                document.getElementById('beer-image-preview-container').style.display = 'block';

                // Image not required for edit
                document.getElementById('beer-image-file').required = false;

                document.getElementById('beer-image-modal').style.display = 'flex';
                document.body.style.overflow = 'hidden';
        }

        // Close modal
        function closeModal() {
                document.getElementById('beer-image-modal').style.display = 'none';
                document.body.style.overflow = '';
                document.getElementById('beer-image-form').reset();
                currentEditingImage = null;
        }

        // Handle form submit
        const imageForm = document.getElementById('beer-image-form');
        if (imageForm && !imageForm.dataset.listenerAttached) {
                imageForm.dataset.listenerAttached = 'true';

                imageForm.addEventListener('submit', async function (e) {
                        e.preventDefault();
                        e.stopImmediatePropagation();

                        const submitBtn = document.getElementById('beer-image-submit-btn');
                        if (submitBtn.disabled) return;

                        const formData = new FormData();
                        formData.append('name', document.getElementById('beer-image-name').value.trim());
                        formData.append('display_order', document.getElementById('beer-image-order').value);
                        formData.append('is_active', document.getElementById('beer-image-is-active').checked ? 'true' : 'false');

                        const imageInput = document.getElementById('beer-image-file');
                        if (imageInput.files.length > 0) {
                                formData.append('image', imageInput.files[0]);
                        }

                        const originalText = submitBtn.textContent;
                        submitBtn.disabled = true;
                        submitBtn.textContent = 'Saving...';

                        try {
                                let url, method;
                                if (currentEditingImage) {
                                        url = `/beer-images/admin/${currentEditingImage.id}`;
                                        method = 'PUT';
                                } else {
                                        url = '/beer-images/admin';
                                        method = 'POST';
                                }

                                const response = await window.WOVCCAuth.authenticatedFetch(url, {
                                        method: method,
                                        body: formData
                                });

                                const data = await response.json();

                                if (data.success) {
                                        showSuccess(currentEditingImage ? 'Beer image updated successfully' : 'Beer image added successfully');
                                        closeModal();
                                        loadBeerImages();
                                } else {
                                        showError('Failed to save beer image: ' + (data.error || 'Unknown error'));
                                }
                        } catch (error) {
                                console.error('Error saving beer image:', error);
                                showError('Failed to save beer image');
                        } finally {
                                submitBtn.disabled = false;
                                submitBtn.textContent = originalText;
                        }
                });
        }

        // Image preview on file select
        const fileInput = document.getElementById('beer-image-file');
        if (fileInput) {
                fileInput.addEventListener('change', function (e) {
                        const file = e.target.files[0];
                        if (file) {
                                const reader = new FileReader();
                                reader.onload = function (event) {
                                        const previewImg = document.getElementById('beer-image-preview');
                                        previewImg.src = event.target.result;
                                        document.getElementById('beer-image-preview-container').style.display = 'block';
                                };
                                reader.readAsDataURL(file);
                        }
                });
        }

        // Delete beer image
        async function deleteImage(image) {
                // Use mobile-friendly modal instead of blocking confirm
                const confirmed = await window.WOVCCModal.confirmDelete(
                        image.name,
                        'This will permanently remove the beer image from the homepage carousel. This action cannot be undone.'
                );

                if (!confirmed) {
                        return;
                }

                try {
                        const response = await window.WOVCCAuth.authenticatedFetch(`/beer-images/admin/${image.id}`, {
                                method: 'DELETE'
                        });

                        const data = await response.json();

                        if (data.success) {
                                showSuccess('Beer image deleted successfully');
                                loadBeerImages();
                        } else {
                                showError('Failed to delete beer image: ' + (data.error || 'Unknown error'));
                        }
                } catch (error) {
                        console.error('Error deleting beer image:', error);
                        showError('Failed to delete beer image');
                }
        }

        // Helper functions
        function debounce(func, wait) {
                let timeout;
                return function executedFunction(...args) {
                        const later = () => {
                                clearTimeout(timeout);
                                func(...args);
                        };
                        clearTimeout(timeout);
                        timeout = setTimeout(later, wait);
                };
        }

        function showError(message) {
                // Use the global notification system from admin-page.js
                if (typeof showNotification === 'function') {
                        showNotification(message, 'error');
                } else if (typeof window.showDomNotification === 'function') {
                        window.showDomNotification(message, 'error');
                } else {
                        console.error(message);
                        if (window.WOVCCModal) {
                                window.WOVCCModal.alert({ title: 'Error', message: message, type: 'danger' });
                        }
                }
        }

        function showSuccess(message) {
                // Use the global notification system from admin-page.js
                if (typeof showNotification === 'function') {
                        showNotification(message, 'success');
                } else if (typeof window.showDomNotification === 'function') {
                        window.showDomNotification(message, 'success');
                } else {
                        console.log(message);
                }
        }

        // Expose loadBeerImages for tab initialization
        window.AdminBeerImages.loadBeerImages = loadBeerImages;

})();
