const migrationKey = "novelforge.product-entry.v5.appearance-migrated";

if (!localStorage.getItem(migrationKey)) {
  localStorage.setItem("novelforge.appearance", "light");
  localStorage.setItem(migrationKey, "true");
}

document.documentElement.dataset.experience = "story-loom-kawaii-atelier-v5";
