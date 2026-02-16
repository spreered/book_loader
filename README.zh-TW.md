# Book Loader

[English](README.md) | [繁體中文](README.zh-TW.md)

Adobe ACSM 電子書 DRM 移除工具 - 支援匿名和 Adobe ID 授權

---

## ⚠️ 法律聲明與使用限制

**使用前請仔細閱讀**

本軟體僅供**教育、研究及個人備份用途**。使用本工具即表示您已閱讀並同意以下條款：

### 法律限制

1. **版權合規**：本工具僅能用於您**合法購買**或擁有明確授權的電子書。未經授權移除受版權保護內容的 DRM 可能違反：
   - 美國數位千禧年著作權法（DMCA）
   - 歐盟著作權指令
   - 您所在司法管轄區的類似著作權保護法律

2. **禁止行為**：以下行為**嚴格禁止**：
   - 商業性重新分發無 DRM 電子書
   - 與未經授權的第三方分享無 DRM 電子書
   - 為盜版或侵犯著作權而規避 DRM
   - 任何違反電子書供應商服務條款的使用

3. **僅供個人使用**：本工具僅用於建立合法購買電子書的個人備份副本，以便在您自己的裝置上使用。

### 免責聲明

- **無擔保**：本軟體按「現狀」提供，不提供任何明示或暗示的擔保。
- **責任限制**：作者和貢獻者對本軟體的任何誤用、法律後果或損害不承擔任何責任。
- **使用者責任**：使用者須自行確保其使用符合所在司法管轄區的適用法律和服務條款。

### 開發者聲明

本專案開發目的為合法的互通性和個人備份。開發者不支持或縱容盜版、侵犯著作權或任何非法活動。

**如果您不同意這些條款或無法確保合法使用，請勿使用本軟體。**

---

## 功能特色

- ✅ 處理 ACSM 檔案，輸出無 DRM 的 EPUB/PDF
- ✅ 支援匿名授權（無需 Adobe 帳號）
- ✅ 支援 Adobe ID 授權（可在多台裝置使用）
- ✅ 無需安裝 Adobe Digital Editions
- ✅ 純 Python 實作，跨平台支援

## 安裝

```bash
# 使用 uv
uv pip install -e .

# 或使用 pip
pip install -e .
```

## 使用方式

### 快速開始

```bash
# 最簡單的方式：直接處理 ACSM（會自動建立匿名授權）
uv run book-loader process book.acsm

# 指定輸出目錄
uv run book-loader process book.acsm -o ~/Books/
```

### 授權管理

#### 建立新授權

```bash
# 方法 1：匿名授權（預設，無需 Adobe 帳號）
uv run book-loader auth create --anonymous

# 方法 2：Adobe ID 授權（最多可在 6 台裝置使用）
uv run book-loader auth create --adobe-id --email your@email.com

# 檢視授權資訊
uv run book-loader auth info

# 重置授權
uv run book-loader auth reset
```

#### 使用現有授權（進階）

如果您已經有 Adobe Digital Editions (ADE) 的授權，可以直接使用：

```bash
# 使用 ADE 的授權目錄
uv run book-loader process book.acsm \
  --auth-dir ~/Library/Application\ Support/Adobe/Digital\ Editions/

# 或使用自訂授權目錄
uv run book-loader process book.acsm --auth-dir /path/to/auth/
```

**注意**：ADE 授權目錄可能同時包含匿名和 Adobe ID 授權。工具會優先使用：
- `activation.xml` + `device.xml` + `devicesalt`（舊格式授權）
- `activation.dat`（ADE 4.5+ 格式）

### 系統資訊

```bash
# 顯示系統資訊
uv run book-loader info
```

## 重要概念

### ACSM 檔案與 Transaction ID

**ACSM (Adobe Content Server Manager)** 不是電子書本身，而是一張「下載憑證」：

1. **Transaction ID 在購買時產生**
   - 每次購買會產生唯一的 Transaction ID
   - 在不同裝置下載同一本書的 ACSM，Transaction ID 相同
   - 即使重新下載 ACSM，Transaction ID 也不會改變

2. **ACSM 只能履行一次**
   - 履行後，ACSM 會綁定到特定的授權
   - Adobe 伺服器會記錄此 Transaction 已被使用
   - 無法在其他裝置或授權上重複使用同一個 ACSM

3. **如何查看 Transaction ID**
   ```bash
   # 查看某個 ACSM 的 Transaction ID
   grep transaction your-book.acsm

   # 查看所有 ACSM 的 Transaction ID
   grep transaction ~/Downloads/*.acsm
   ```

### 授權類型比較

| 授權類型 | 需要帳號 | 裝置限制 | 使用情境 |
|---------|---------|---------|---------|
| **匿名授權** | ❌ 否 | ⚠️ 僅單一裝置 | 單一裝置，注重隱私 |
| **Adobe ID** | ✅ 是 | ✅ 最多 6 台裝置 | 多裝置同步 |

### 多裝置使用建議

**❌ 錯誤做法：**
```bash
# 在裝置 A 履行 ACSM
book-loader process book.acsm

# 在裝置 B 再次履行同一個 ACSM
book-loader process book.acsm  # ❌ 會失敗！Transaction 已被使用
```

**✅ 正確做法：**
```bash
# 在裝置 A 履行並移除 DRM
book-loader process book.acsm -o ~/Books/
# 產生：~/Books/book.epub（無 DRM）

# 將無 DRM 的檔案複製到裝置 B
# 可直接使用，無需重新履行 ACSM
```

## 常見問題

### Q: 為什麼出現「E_LIC_ALREADY_FULFILLED_BY_ANOTHER_USER」錯誤？

**原因**：此 ACSM (Transaction) 已被某個授權使用過。

**可能情況**：
1. 之前在 Adobe Digital Editions 中開啟過此書
2. 用其他工具處理過此 ACSM
3. 重新下載同一本書的 ACSM（Transaction ID 相同）

**解決方案**：
- 如果之前在 ADE 開啟過：使用 `--auth-dir` 指定 ADE 的授權目錄
- 如果檔案已刪除：無法重新履行，需找回原始電子書檔案
- 如果是全新的書：確認未在其他授權上開啟過

### Q: 如何檢查某本書是否已被履行？

檢查錯誤訊息中的 UUID：

```bash
# 錯誤訊息範例：
# E_LIC_ALREADY_FULFILLED_BY_ANOTHER_USER ... urn:uuid:2b60b2eb-...

# 查看您的授權 UUID
grep "user>" ~/.config/book-loader/.adobe/activation.xml
```

如果 UUID 相符，表示是您的授權履行的；不相符則是其他授權履行的。

### Q: 可以同時使用多個授權嗎？

可以！使用 `--auth-dir` 指定不同的授權目錄：

```bash
# 使用授權 A
book-loader process book1.acsm --auth-dir ~/auth-a/

# 使用授權 B
book-loader process book2.acsm --auth-dir ~/auth-b/
```

### Q: 如何備份授權？

匿名授權需要備份三個檔案：
```bash
# 預設位置：~/.config/book-loader/.adobe/
cp ~/.config/book-loader/.adobe/activation.xml ~/backup/
cp ~/.config/book-loader/.adobe/device.xml ~/backup/
cp ~/.config/book-loader/.adobe/devicesalt ~/backup/
```

Adobe ID 授權會同步到 Adobe 伺服器，但仍建議備份這些檔案。

### Q: 處理失敗後可以重試嗎？

取決於失敗階段：
- ✅ **履行成功但下載失敗**：可重試（Transaction 未消耗）
- ✅ **DRM 移除失敗**：可重試（已下載的加密檔案仍存在）
- ❌ **履行成功且下載完成**：Transaction 已消耗，無法重試

## 授權條款

GPLv3

本專案整合了以下開源程式碼：
- [acsm-calibre-plugin](https://github.com/Leseratte10/acsm-calibre-plugin) - GPLv3
- [DeDRM_tools](https://github.com/noDRM/DeDRM_tools)

## 免責聲明

**重要**：本工具僅供個人合法使用合法購買的電子書。

**違反著作權法或服務條款可能導致民事和刑事處罰。**使用者須自行承擔全部責任，確保其使用符合所在司法管轄區的所有適用法律和法規。

開發者明確聲明不對本軟體的任何誤用負責。
