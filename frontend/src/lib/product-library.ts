export type PhotoAnalysisRecord = {
  product_type: string;
  visible_features: string[];
  product_title: string;
  visual_description: string;
  background_suggestions: string[];
  composition_suggestions: string[];
  lighting_recommendations: string[];
  framing_recommendations: string[];
  color_palette: string[];
  confidence_note: string;
};

export type SavedProduct = {
  id: string;
  name: string;
  createdAt: string;
  image: Blob;
  imageType: string;
  analysis: PhotoAnalysisRecord | null;
};

const DB_NAME = "zorvi-product-library";
const STORE = "products";

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    if (typeof indexedDB === "undefined") return reject(new Error("Browser storage is unavailable."));
    const request = indexedDB.open(DB_NAME, 1);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(STORE)) db.createObjectStore(STORE, { keyPath: "id" });
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error ?? new Error("Could not open product storage."));
  });
}

export async function saveProduct(product: SavedProduct): Promise<void> {
  const db = await openDb();
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(STORE, "readwrite");
    tx.objectStore(STORE).put(product);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error ?? new Error("Could not save product."));
    tx.onabort = () => reject(tx.error ?? new Error("Saving product was cancelled."));
  });
  db.close();
}

export async function getProducts(): Promise<SavedProduct[]> {
  const db = await openDb();
  const products = await new Promise<SavedProduct[]>((resolve, reject) => {
    const tx = db.transaction(STORE, "readonly");
    const request = tx.objectStore(STORE).getAll();
    request.onsuccess = () => resolve((request.result as SavedProduct[]).sort((a, b) => b.createdAt.localeCompare(a.createdAt)));
    request.onerror = () => reject(request.error ?? new Error("Could not load saved products."));
  });
  db.close();
  return products;
}

export async function getProduct(id: string): Promise<SavedProduct | null> {
  const db = await openDb();
  const product = await new Promise<SavedProduct | null>((resolve, reject) => {
    const request = db.transaction(STORE, "readonly").objectStore(STORE).get(id);
    request.onsuccess = () => resolve((request.result as SavedProduct | undefined) ?? null);
    request.onerror = () => reject(request.error ?? new Error("Could not load product."));
  });
  db.close();
  return product;
}

export async function deleteProduct(id: string): Promise<void> {
  const db = await openDb();
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(STORE, "readwrite");
    tx.objectStore(STORE).delete(id);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error ?? new Error("Could not delete product."));
  });
  db.close();
}

export function createProductId(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export const PRODUCT_HANDOFF_KEY = "zorvi.photo-assistant.handoff.v1";
