/**
 * Last-clicked row tracker — sessionStorage backed.
 *
 * Cilj: kad korisnik klikne red u Sessions/Live/History tabeli i navigira
 * na detail, pa se vrati nazad → red ostaje highlighted da zna gdje je bio.
 *
 * sessionStorage je idealan jer se briše kad se browser tab zatvori
 * (state ne preživljava session, što je ono što korisnik očekuje).
 */

const KEY_PREFIX = 'bitlab.lastSelected.';

export function setLastSelected(table: string, id: string | number): void {
  try {
    sessionStorage.setItem(KEY_PREFIX + table, String(id));
  } catch { /* ignore quota / disabled */ }
}

export function getLastSelected(table: string): string | null {
  try {
    return sessionStorage.getItem(KEY_PREFIX + table);
  } catch { return null }
}

export function isSelected(table: string, id: string | number): boolean {
  return getLastSelected(table) === String(id);
}
