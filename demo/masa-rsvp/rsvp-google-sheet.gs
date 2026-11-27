// Devetify — RSVP cavablarını Google Sheet-ə yazan skript
// Google Sheet → Genişləndirmələr (Extensions) → Apps Script → bunu yapışdırın → Yerləşdir (Deploy)
function doPost(e) {
  var sh = SpreadsheetApp.getActiveSpreadsheet().getSheets()[0];
  if (sh.getLastRow() === 0) sh.appendRow(["Tarix", "Ad Soyad", "Cavab", "Nəfər sayı", "Mesaj"]);
  var p = e.parameter;
  sh.appendRow([new Date(), p.ad || "", p.cavab || "", Number(p.say || 0), p.mesaj || ""]);
  return ContentService.createTextOutput("ok");
}
