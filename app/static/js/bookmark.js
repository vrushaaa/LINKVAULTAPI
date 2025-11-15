
async function openBookmarkModal(id) {
 const response = await fetch(`/api/bookmarks/${id}`);
 const data = await response.json();

 document.getElementById("modal-title").textContent = data.bookmark.title;
 document.getElementById("modal-url").textContent = data.bookmark.url;
 document.getElementById("modal-url").href = data.bookmark.url;

 document.getElementById("modal-short").textContent =
  data.bookmark.full_short_url;
 document.getElementById("modal-short").href =
  data.bookmark.full_short_url;

 document.getElementById("modal-created").textContent =
  data.bookmark.created_at;

 const tagContainer = document.getElementById("modal-tags");
 tagContainer.innerHTML = "";
 data.bookmark.tags.forEach((t) => {
  const span = document.createElement("span");
  span.className =
   "bg-[#243c1a] text-[#c1e328] px-3 py-1 text-sm rounded-full";
  span.textContent = t;
  tagContainer.appendChild(span);
 });

 document.getElementById("modal-notes").textContent =
  data.bookmark.notes || "No notes available.";

 document.getElementById("bookmarkModal").classList.remove("hidden");
}

function closeBookmarkModal() {
 document.getElementById("bookmarkModal").classList.add("hidden");
}

async function showQR(id) {
 const response = await fetch(`/api/bookmarks/${id}/qr`);
 const data = await response.json();

 document.getElementById(
  "qrCodeContainer"
 ).innerHTML = `<img src="${data.qr_data_uri}" class="rounded-lg" />`;

 document.getElementById("qrTitle").textContent = data.qr_title;
 document.getElementById("qrURL").textContent = data.qr_url;
 document.getElementById("qrImage").classList.remove("hidden");
}

function closeQR() {
 document.getElementById("qrImage").classList.add("hidden");
}

feather.replace();

let bookmarkIdToDelete = null;
function openDeleteModal(id) {
 bookmarkIdToDelete = id;
 document.getElementById("deleteModal").classList.remove("hidden");
}
function closeDeleteModal() {
 bookmarkIdToDelete = null;
 document.getElementById("deleteModal").classList.add("hidden");
}

async function confirmDelete() {
 if (bookmarkIdToDelete) {
  const response = await fetch(`/api/bookmarks/${bookmarkIdToDelete}`, {
   method: "DELETE",
  });

  if (response.ok) {
   // Successfully deleted
   closeDeleteModal();
   location.reload();
  } else {
   alert("Failed to delete the bookmark.");
  }
 }
}

//edit modal
let currentBookmarkid = null;

async function openEditModal(id) {
 const res = await fetch(`/api/bookmarks/${id}`);
 const data = await res.json();
 const b = data.bookmark;

 document.getElementById("editTitle").value = b.title || "";
 document.getElementById("editNotes").value = b.notes || "";
 document.getElementById("editTags").value = b.tags.join(", ");

 document.getElementById("editArchive").value = b.archived
  ? "true"
  : "false";

 currentBookmarkid = id;
 document.getElementById("editModal").classList.remove("hidden");
}

function closeEditModal() {
 currentBookmarkid = null;
 document.getElementById("editModal").classList.add("hidden");
}

async function updateBookmark(event) {
 event.preventDefault();

 const data = {
  title: document.getElementById("editTitle").value,
  notes: document.getElementById("editNotes").value,
  archived: document.getElementById("editArchive").value === "true",
  tags: document
   .getElementById("editTags")
   .value.split(",")
   .map((t) => t.trim())
   .filter((t) => t.length > 0),
 };

 const response = await fetch(`/api/bookmarks/${currentBookmarkid}`, {
  method: "PUT",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(data),
 });

 if (response.ok) {
  closeEditModal();
  location.reload();
 } else {
  alert("Failed to update the bookmark.");
 }
}
