# WooCommerce 3D Ring Viewer - Deployment Instructions

Follow these steps to deploy the products and the 360-degree interactive viewer on the live WordPress server.

## 📦 What's Included:
1. `raw_images/` — Product and variation images.
2. `360-assets/` — 3D GLTF files and lighting environments.
3. `ring-360-viewer-plugin.zip` — The 3D viewer plugin.
4. `test_product.csv` — WooCommerce product data.

---

## 🛠️ Step-by-Step Setup

### Step 1: Upload Assets via FTP or File Manager
Using cPanel File Manager or FTP (e.g., FileZilla), upload the media folders to your server's uploads directory:
1. Upload the `raw_images` folder to: `/wp-content/uploads/`
2. Upload the `360-assets` folder to: `/wp-content/uploads/`

### Step 2: Install the 3D Viewer Plugin
1. Log into your WordPress admin panel.
2. Navigate to **Plugins → Add New → Upload Plugin**.
3. Choose the `ring-360-viewer-plugin.zip` file.
4. Click **Install Now** and then **Activate**.

### Step 3: WooCommerce Product Import
1. Go to **WooCommerce → Products → Import**.
2. Upload the `test_product.csv`.
3. Map the following columns carefully:
   - **Type** → Select **Type** from the dropdown (CRITICAL).
   - **SKU** → Select **SKU**.
   - **Name** → Select **Name**.
   - **Parent** → Select **Parent**.
   - **Categories** → Select **Categories**.
   - **Images** → Select **Images**.
4. Click **Run the Importer**.

---

> ⚠️ **IMPORTANT NOTE FOR DEVELOPERS:** 
> Before importing the CSV, ensure that the domain URLs inside the CSV match your live site (e.g., change `http://localhost` to `https://clientdomain.com`).
