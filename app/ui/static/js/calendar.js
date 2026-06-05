// Download template function (global scope)
window.downloadTemplate = function() {
  const importType = document.getElementById("importType").value;
  const url = `/api/calendar/exports/csv?export_type=${importType}&template=true`;
  window.location.href = url;
};

document.addEventListener("DOMContentLoaded", function () {
  const eventModal = document.getElementById("eventModal");
  const importModal = document.getElementById("importModal");
  const exportModal = document.getElementById("exportModal");
  const memberSelect = document.getElementById("eventMemberSelect");
  const dateInput = document.getElementById("eventDateInput");
  const eventTypeSelect = document.getElementById("eventTypeSelect");
  const titleInput = document.querySelector('input[name="title"]');

  let importPreviewData = null;

  // Section toggle functionality
  const sectionToggles = document.querySelectorAll(".section-toggle");
  console.log("Found section toggles:", sectionToggles.length);
  sectionToggles.forEach(toggle => {
    toggle.addEventListener("click", function() {
      console.log("Toggle clicked:", this.dataset.section);
      const sectionName = this.dataset.section;
      const sectionPanel = document.getElementById(`section-${sectionName}`);
      console.log("Section panel:", sectionPanel);
      if (sectionPanel) {
        sectionPanel.classList.toggle("minimized");
        this.textContent = sectionPanel.classList.contains("minimized") ? "+" : "−";
      } else {
        console.error("Section panel not found:", `section-${sectionName}`);
      }
    });
  });

  // Chat functionality
  const chatMessages = document.getElementById("chatMessages");
  const chatInput = document.getElementById("chatInput");
  const sendChatBtn = document.getElementById("sendChatBtn");

  // Store conversation history
  let conversationHistory = [];

  function addChatMessage(content, type = "user") {
    const messageDiv = document.createElement("div");
    messageDiv.className = `chat-message ${type}`;

    const avatarDiv = document.createElement("div");
    avatarDiv.className = "message-avatar";
    avatarDiv.textContent = type === "user" ? "U" : "AI";

    const contentDiv = document.createElement("div");
    contentDiv.className = "message-content";
    contentDiv.textContent = content;

    messageDiv.appendChild(avatarDiv);
    messageDiv.appendChild(contentDiv);
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // Add to conversation history
    conversationHistory.push({
      role: type === "user" ? "user" : "assistant",
      content: content
    });
  }

  async function sendChatMessage() {
    const message = chatInput.value.trim();
    if (!message) return;

    addChatMessage(message, "user");
    chatInput.value = "";
    sendChatBtn.disabled = true;
    sendChatBtn.textContent = "送信中...";

    try {
      // Get current year and month from URL or page
      const urlParams = new URLSearchParams(window.location.search);
      const year = urlParams.get("year") || new Date().getFullYear();
      const month = urlParams.get("month") || (new Date().getMonth() + 1);

      const response = await fetch("/api/chat/dify-proxy", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message,
          year: parseInt(year),
          month: parseInt(month),
          conversation_history: conversationHistory
        }),
      });

      const result = await response.json();

      if (result.ok) {
        addChatMessage(result.data.reply, "assistant");
      } else {
        addChatMessage("エラー: " + (result.message || "不明なエラー"), "system");
      }
    } catch (error) {
      addChatMessage("エラー: " + error.message, "system");
    } finally {
      sendChatBtn.disabled = false;
      sendChatBtn.textContent = "送信";
    }
  }

  if (sendChatBtn) {
    sendChatBtn.addEventListener("click", sendChatMessage);
  }

  if (chatInput) {
    chatInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendChatMessage();
      }
    });
  }

  // Tab functionality
  const tabButtons = document.querySelectorAll(".tab-button");
  tabButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const tabId = button.dataset.tab;

      // Remove active class from all buttons and contents
      tabButtons.forEach((btn) => btn.classList.remove("active"));
      document.querySelectorAll(".tab-content").forEach((content) => {
        content.classList.remove("active");
      });

      // Add active class to clicked button and corresponding content
      button.classList.add("active");
      const tabContent = document.getElementById(`tab-${tabId}`);
      if (tabContent) {
        tabContent.classList.add("active");
      }
    });
  });

  function openModal(modal) {
    if (!modal) return;
    modal.classList.add("is-open");
    modal.setAttribute("aria-hidden", "false");
    const firstInput = modal.querySelector("input, select, textarea, button");
    if (firstInput) firstInput.focus();
  }

  function closeModal(modal) {
    if (!modal) return;
    modal.classList.remove("is-open");
    modal.setAttribute("aria-hidden", "true");
  }

  function filterByDepartment() {
    const select = document.getElementById("departmentFilter");
    const deptId = select.value;
    const url = new URL(window.location);
    if (deptId) {
      url.searchParams.set("department_id", deptId);
    } else {
      url.searchParams.delete("department_id");
    }
    window.location.href = url.toString();
  }

  // Import functionality
  const previewImportBtn = document.getElementById("previewImportBtn");
  
  if (previewImportBtn) {
    previewImportBtn.addEventListener("click", async () => {
    const importType = document.getElementById("importType").value;
      const fileInput = document.getElementById("importFile");
      const file = fileInput.files[0];

      if (!file) {
        alert("CSVファイルを選択してください");
        return;
      }

      const formData = new FormData();
      formData.append("import_type", importType);
      formData.append("file", file);

      // Show loading overlay
      const loadingOverlay = document.getElementById("importLoadingOverlay");
      loadingOverlay.style.display = "flex";

      try {
        const response = await fetch("/api/calendar/imports/csv/preview", {
          method: "POST",
          body: formData,
        });

        const result = await response.json();

        if (result.ok) {
          importPreviewData = result.data;
          displayImportPreview(result.data);
          document.getElementById("previewImportBtn").style.display = "none";
          document.getElementById("executeImportBtn").style.display = "inline-block";
        } else {
          alert("プレビューに失敗しました: " + (result.message || "不明なエラー"));
        }
      } catch (error) {
        alert("プレビューに失敗しました: " + error.message);
      } finally {
        // Hide loading overlay
        loadingOverlay.style.display = "none";
      }
    });
  }

  function displayImportPreview(preview) {
    const previewDiv = document.getElementById("importPreview");
    const contentDiv = document.getElementById("importPreviewContent");

    let html = `
      <p>全行数: ${preview.total_rows}</p>
      <p>有効行: ${preview.valid_rows}</p>
      <p>無効行: ${preview.invalid_rows}</p>
    `;

    if (preview.invalid_rows > 0) {
      html += "<h4>エラー行:</h4><ul>";
      preview.rows.filter(r => r.status === "invalid").forEach(row => {
        html += `<li>行 ${row.row_number}: `;
        row.errors.forEach(err => {
          html += `${err.field} - ${err.message}<br>`;
        });
        html += "</li>";
      });
      html += "</ul>";
    }

    contentDiv.innerHTML = html;
    previewDiv.style.display = "block";
  }

  const executeImportBtn = document.getElementById("executeImportBtn");
  if (executeImportBtn) {
    executeImportBtn.addEventListener("click", async () => {
      if (!importPreviewData) {
        alert("プレビューを実行してください");
        return;
      }

      const importType = document.getElementById("importType").value;
      const importMode = document.querySelector('input[name="importMode"]:checked').value;
      const validRows = importPreviewData.rows.filter(r => r.status === "valid").map(r => r.data);

      if (validRows.length === 0) {
        alert("インポート可能な行がありません");
        return;
      }

      const modeText = importMode === "replace" ? "上書き（既存データを削除）" : "追加";
      if (!confirm(`${validRows.length}件のデータを${modeText}でインポートします。よろしいですか？`)) {
        return;
      }

      // Show loading overlay
      const loadingOverlay = document.getElementById("importLoadingOverlay");
      loadingOverlay.style.display = "flex";
      loadingOverlay.querySelector(".loading-text").textContent = "インポート中...";

      try {
        const response = await fetch("/api/calendar/imports/csv/execute", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            import_type: importPreviewData.import_type,
            rows: validRows,
            mode: importMode,
          }),
        });

        const result = await response.json();

        if (result.ok) {
          alert(`インポートが完了しました。成功: ${result.data.success_count}件`);
          closeModal(importModal);
          location.reload();
        } else {
          alert("インポートに失敗しました: " + (result.message || "不明なエラー"));
        }
      } catch (error) {
        alert("インポートに失敗しました: " + error.message);
      } finally {
        // Hide loading overlay
        loadingOverlay.style.display = "none";
        loadingOverlay.querySelector(".loading-text").textContent = "処理中...";
      }
    });
  }

  // Export functionality
  const exportTypeSelect = document.getElementById("exportType");
  if (exportTypeSelect) {
    exportTypeSelect.addEventListener("change", () => {
      const exportType = exportTypeSelect.value;
      const monthSelector = document.getElementById("monthSelector");
      monthSelector.style.display = exportType === "monthly" ? "block" : "none";
    });
  }

  const executeExportBtn = document.getElementById("executeExportBtn");
  if (executeExportBtn) {
    executeExportBtn.addEventListener("click", async () => {
    const exportType = document.getElementById("exportType").value;
    let url = `/api/calendar/exports/csv?export_type=${exportType}`;

    if (exportType === "monthly") {
      const yearMonth = document.getElementById("exportYearMonth").value;
      if (!yearMonth) {
        alert("年月を指定してください");
        return;
      }
      const [year, month] = yearMonth.split("-");
      url += `&year=${year}&month=${month}`;
    }

    window.location.href = url;
    closeModal(exportModal);
    });
  }

  // Reset import modal when closed
  if (importModal) {
    importModal.addEventListener("click", (event) => {
      if (event.target === importModal) {
        document.getElementById("importFile").value = "";
        document.getElementById("importPreview").style.display = "none";
        document.getElementById("previewImportBtn").style.display = "inline-block";
        document.getElementById("executeImportBtn").style.display = "none";
        importPreviewData = null;
      }
    });
  }

  document.querySelectorAll("[data-open-modal]").forEach((button) => {
    button.addEventListener("click", () => {
      const modal = document.getElementById(button.dataset.openModal);
      openModal(modal);
    });
  });

  document.querySelectorAll("[data-open-event-modal]").forEach((button) => {
    button.addEventListener("click", () => {
      // Reset modal to create mode
      eventModal.dataset.editMode = "false";
      eventModal.dataset.eventId = "";
      
      const modalTitle = document.getElementById("eventModalTitle");
      if (modalTitle) modalTitle.textContent = "予定を登録";
      
      const eventForm = eventModal?.querySelector('form');
      if (eventForm) {
        eventForm.action = "/ui/events/create";
      }
      
      // Reset submit button text
      const submitBtn = eventForm?.querySelector('button[type="submit"]');
      if (submitBtn) submitBtn.textContent = "登録";
      
      // Hide delete button
      const deleteBtn = document.getElementById("deleteEventBtn");
      if (deleteBtn) deleteBtn.style.display = "none";
      
      // Reset memo field
      const memoInput = document.querySelector('input[name="memo"]');
      if (memoInput) memoInput.value = "";
      
      if (memberSelect) memberSelect.value = button.dataset.memberId || "";
      if (dateInput) dateInput.value = button.dataset.eventDate || "";
      if (titleInput) titleInput.value = "";
      if (eventTypeSelect) eventTypeSelect.value = "";
      openModal(eventModal);
    });
  });

  // Handle edit event click
  document.querySelectorAll("[data-edit-event]").forEach((pill) => {
    pill.addEventListener("click", () => {
      console.log("Edit event clicked:", pill.dataset);
      
      if (memberSelect) {
        memberSelect.value = pill.dataset.memberId || "";
        console.log("memberSelect set to:", memberSelect.value);
      }
      if (dateInput) {
        dateInput.value = pill.dataset.eventDate || "";
        console.log("dateInput set to:", dateInput.value);
      }
      if (titleInput) {
        titleInput.value = pill.dataset.title || "";
        console.log("titleInput set to:", titleInput.value);
      }
      if (eventTypeSelect) {
        eventTypeSelect.value = pill.dataset.eventTypeId || "";
        console.log("eventTypeSelect set to:", eventTypeSelect.value);
      }
      
      // Set memo field
      const memoInput = document.querySelector('input[name="memo"]');
      if (memoInput) {
        memoInput.value = pill.dataset.memo || "";
        console.log("memoInput set to:", memoInput.value);
      }
      
      // Set edit mode
      eventModal.dataset.editMode = "true";
      eventModal.dataset.eventId = pill.dataset.eventId;
      
      // Update modal title
      const modalTitle = document.getElementById("eventModalTitle");
      if (modalTitle) modalTitle.textContent = "予定を編集";
      
      // Change form action to edit endpoint
      const eventForm = eventModal?.querySelector('form');
      if (eventForm) {
        eventForm.action = `/ui/events/${pill.dataset.eventId}/edit`;
      }
      
      // Change submit button text
      const submitBtn = eventForm?.querySelector('button[type="submit"]');
      if (submitBtn) submitBtn.textContent = "更新";
      
      // Show delete button
      const deleteBtn = document.getElementById("deleteEventBtn");
      if (deleteBtn) {
        deleteBtn.style.display = "inline-block";
        deleteBtn.onclick = () => {
          if (confirm("この予定を削除しますか？")) {
            fetch(`/ui/events/${pill.dataset.eventId}/delete`, { method: "POST" })
              .then(() => window.location.reload());
          }
        };
      }
      
      openModal(eventModal);
    });
  });

  // Handle edit program schedule click
  document.querySelectorAll("[data-edit-program-schedule]").forEach((pill) => {
    pill.addEventListener("click", () => {
      console.log("Edit program schedule clicked:", pill.dataset);
      
      const programScheduleModal = document.getElementById("programScheduleModal");
      const programSelect = document.getElementById("programSelect");
      const programIdInput = document.getElementById("programIdInput");
      const programNameInput = document.getElementById("programNameInput");
      const programNameLabel = document.getElementById("programNameLabel");
      const studioIdInput = document.getElementById("studioIdInput");
      const programDateInput = document.getElementById("programDateInput");
      const scheduleIdInput = document.getElementById("scheduleIdInput");
      
      if (programSelect) programSelect.value = pill.dataset.programId || "";
      if (programIdInput) programIdInput.value = pill.dataset.programId || "";
      if (programNameInput) programNameInput.value = pill.dataset.programName || "";
      if (studioIdInput) studioIdInput.value = pill.dataset.studioId || "";
      if (programDateInput) programDateInput.value = pill.dataset.eventDate || "";
      if (scheduleIdInput) scheduleIdInput.value = pill.dataset.scheduleId || "";
      
      // Show/hide free text input based on selection
      if (programSelect && programNameLabel) {
        if (programSelect.value === "") {
          programNameLabel.style.display = "block";
        } else {
          programNameLabel.style.display = "none";
        }
      }
      
      // Change form action to edit endpoint
      const programForm = programScheduleModal?.querySelector('form');
      if (programForm) {
        programForm.action = `/ui/program-schedules/${pill.dataset.scheduleId}/edit`;
      }
      
      // Change submit button text
      const submitBtn = programForm?.querySelector('button[type="submit"]');
      if (submitBtn) submitBtn.textContent = "更新";
      
      // Show delete button
      const deleteBtn = document.getElementById("deleteProgramScheduleBtn");
      if (deleteBtn) {
        deleteBtn.style.display = "inline-block";
        deleteBtn.onclick = () => {
          if (confirm("この番組スケジュールを削除しますか？")) {
            fetch(`/ui/program-schedules/${pill.dataset.scheduleId}/delete`, { method: "POST" })
              .then(() => window.location.reload());
          }
        };
      }
      
      // Update modal title
      const modalTitle = document.getElementById("programScheduleModalTitle");
      if (modalTitle) modalTitle.textContent = "番組スケジュールを編集";
      
      openModal(programScheduleModal);
    });
  });

  // Handle open program schedule modal click (create mode)
  document.querySelectorAll("[data-open-program-schedule-modal]").forEach((button) => {
    button.addEventListener("click", () => {
      const programScheduleModal = document.getElementById("programScheduleModal");
      const programSelect = document.getElementById("programSelect");
      const programIdInput = document.getElementById("programIdInput");
      const programNameInput = document.getElementById("programNameInput");
      const programNameLabel = document.getElementById("programNameLabel");
      const studioIdInput = document.getElementById("studioIdInput");
      const programDateInput = document.getElementById("programDateInput");
      const scheduleIdInput = document.getElementById("scheduleIdInput");
      
      // Reset to create mode
      if (scheduleIdInput) scheduleIdInput.value = "";
      if (programSelect) programSelect.value = "";
      if (programIdInput) programIdInput.value = "";
      if (programNameInput) programNameInput.value = "";
      if (studioIdInput) studioIdInput.value = button.dataset.studioId || "";
      if (programDateInput) programDateInput.value = button.dataset.eventDate || "";
      
      // Show free text input by default
      if (programNameLabel) programNameLabel.style.display = "block";
      
      // Change form action to create endpoint
      const programForm = programScheduleModal?.querySelector('form');
      if (programForm) {
        programForm.action = "/ui/program-schedules/create";
      }
      
      // Change submit button text
      const submitBtn = programForm?.querySelector('button[type="submit"]');
      if (submitBtn) submitBtn.textContent = "登録";
      
      // Hide delete button
      const deleteBtn = document.getElementById("deleteProgramScheduleBtn");
      if (deleteBtn) deleteBtn.style.display = "none";
      
      // Update modal title
      const modalTitle = document.getElementById("programScheduleModalTitle");
      if (modalTitle) modalTitle.textContent = "番組スケジュールを登録";
      
      openModal(programScheduleModal);
    });
  });

  // Handle program select change
  const programSelect = document.getElementById("programSelect");
  const programIdInput = document.getElementById("programIdInput");
  const programNameLabel = document.getElementById("programNameLabel");
  if (programSelect && programNameLabel && programIdInput) {
    programSelect.addEventListener("change", () => {
      if (programSelect.value === "") {
        programNameLabel.style.display = "block";
        programIdInput.value = "";
      } else {
        programNameLabel.style.display = "none";
        programIdInput.value = programSelect.value;
      }
    });
  }

  // Handle apply regular schedule button
  const applyRegularScheduleBtn = document.getElementById("applyRegularScheduleBtn");
  const regularScheduleSelect = document.getElementById("regularScheduleSelect");
  if (applyRegularScheduleBtn && regularScheduleSelect) {
    applyRegularScheduleBtn.addEventListener("click", () => {
      const regularScheduleId = regularScheduleSelect.value;
      if (!regularScheduleId) {
        alert("レギュラーを選択してください");
        return;
      }

      // Get current year and month from URL
      const urlParams = new URLSearchParams(window.location.search);
      const year = urlParams.get("year") || new Date().getFullYear();
      const month = urlParams.get("month") || new Date().getMonth() + 1;

      const formData = new FormData();
      formData.append("regular_schedule_id", regularScheduleId);
      formData.append("year", year);
      formData.append("month", month);

      fetch("/ui/regular-schedules/apply", {
        method: "POST",
        body: formData,
      })
        .then(() => window.location.reload())
        .catch((err) => console.error("Error applying regular schedule:", err));
    });
  }

  // Auto-fill title when event type is selected
  if (eventTypeSelect && titleInput) {
    eventTypeSelect.addEventListener("change", () => {
      const selectedOption = eventTypeSelect.options[eventTypeSelect.selectedIndex];
      if (selectedOption && selectedOption.value && selectedOption.dataset.name) {
        titleInput.value = selectedOption.dataset.name;
      }
    });
  }

  // Handle event form submission
  const eventForm = eventModal?.querySelector('form');
  const hiddenEventTypeId = document.getElementById("hiddenEventTypeId");
  if (eventForm && hiddenEventTypeId) {
    eventForm.addEventListener("submit", (e) => {
      // Copy the value from select to hidden input
      const value = eventTypeSelect?.value || "";
      if (value) {
        hiddenEventTypeId.value = value;
        hiddenEventTypeId.name = "event_type_id";
      } else {
        hiddenEventTypeId.removeAttribute("name");
      }
    });
  }

  document.querySelectorAll("[data-close-modal]").forEach((button) => {
    button.addEventListener("click", () => closeModal(button.closest(".modal-backdrop")));
  });

  document.querySelectorAll(".modal-backdrop").forEach((backdrop) => {
    backdrop.addEventListener("click", (event) => {
      if (event.target === backdrop) closeModal(backdrop);
    });
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      document.querySelectorAll(".modal-backdrop.is-open").forEach(closeModal);
    }
  });
});
