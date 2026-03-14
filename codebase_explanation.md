# CliniPaws: Ultra-Detailed Codebase & Logic Documentation

This document provides an exhaustive, code-level explanation of the **CliniPaws** Livestock Disease Prediction system. It is designed to explain not just what each file does, but *how* the code achieves its goals.

---

## 🏗️ Core Engineering & System Design

### 1. The Prediction Engine (`Logistic Regression classifier/`)
The system uses a sophisticated hybrid approach to diagnosis, combining expert rules with modern AI embeddings.

#### `Logistic_Regression.py`
This file contains the `Logistic_Regression_classifier` function, which is the primary diagnosis entry point.
*   **Expert Rules Layer (`check_rule_based_overrides`)**: Before invoking AI, the code checks for "hard" clinical markers. For example, if "painless lumps" and "skin nodules" are both present, it returns "Lumpy Skin Disease" with 100% confidence, bypassing the ML model to ensure zero false negatives for critical diseases.
*   **AI Embedding Layer (`get_distilbert_embeddings`)**: 
    *   It uses `DistilBertTokenizer` to convert natural language symptoms into tokens.
    *   The `DistilBertModel` generates a 768-dimensional vector (the `[CLS]` token) representing the semantic meaning of the symptoms.
    *   **Logic**: This allows the system to understand that "painful legs" and "difficulty walking" are semantically similar even if the exact words differ.
*   **Classification Layer**: The embedding is fed into a pre-trained `LogisticRegression` model.
*   **Fallback system**: If `transformers` (the library for DistilBERT) isn't installed, the code catches the `ImportError` and falls back to a **TF-IDF Vectorizer**, ensuring the app remains functional in restricted environments.

#### `Roboflow/detector.py`
Handles image-based skin disease detection.
*   **Multi-Model Inference**: The `SkinDiseaseDetector` class initializes an `InferenceHTTPClient`. It doesn't rely on just one model; it queries `lumpy-skin-wab9r/1` (specialized) and `cattle-disease-pnjdc/3` (general) in parallel.
*   **The Merging Logic (`_combine_results`)**: 
    *   The code iterates through all model results.
    *   It treats "Healthy", "Normal", and "No Disease" as negatives.
    *   **Priority**: If the Lumpy Skin model detects a disease, that result takes priority. If not, it falls back to the general model. This "ensemble" approach maximizes detection rates for skin lesions.
*   **In-Place Annotation (`draw_detections`)**: Uses OpenCV (`cv2`) to calculate bounding box coordinates from Roboflow's JSON response and draws green rectangles and labels directly onto the image.

---

## 📄 The Bilingual PDF Pipeline (`livestock_disease_prediction/pdf_utils.py`)
Rendering Urdu in a PDF is technically challenging because standard PDF engines don't handle Right-to-Left (RTL) or character joining (ligatures) natively.

### The 3-Stage Rendering Logic:
1.  **Reshaping**: `arabic_reshaper.reshape()` takes a raw Urdu string and replaces characters with their contextual forms (initial, medial, or final) so they connect properly.
2.  **BiDi Reordering**: `bidi_display()` applies the Unicode Bidirectional Algorithm. It reverses the visual order of the string so it flows from right to left while keeping English text (like medicine names) left-to-right.
3.  **Font Injection**: The code registers `NotoNaskhArabic-Regular.ttf` using ReportLab's `TTFont` and `pdfmetrics`.
*   **`_preprocess_html` Function**: This is a critical utility that uses Regex (`re.compile`) to find Urdu chunks within HTML tags (like `<b>` or `<br/>`). It wraps only the Urdu parts in `<font name="NotoNaskhArabic">` tags, allowing seamless English/Urdu mixing in the same paragraph.

---

## 🔒 User Security & Moderation (`accounts/`)

### 🔑 3-Step Password Reset logic (`views.py`)
Instead of a simple "reset link," this system uses a high-security OTP flow:
1.  **`ForgotPasswordView`**: Generates a 6-digit `PasswordResetOTP` and sends it via Gmail SMTP using `send_mail`.
2.  **`VerifyOTPView`**: Checks if the OTP is correct, matches the user's email, hasn't been used yet, and is less than 10 minutes old.
3.  **`ResetPasswordView`**: Only allows access if a specific session flag (`otp_verified`) is set, preventing "URL-skipping" attacks.

### 🛡️ Moderation Logic
*   **Blocking**: When an admin sets `is_blocked = True`, the `BlockedUserMiddleware` interceptor catches every request. If the user is blocked, it forces a redirect to the `blocked/` URL via `redirect('blocked')`.
*   **Appeals**: Blocked users can submit a `ContactMessage`. In `admin_messages.html`, admins can "React" to these messages. 
*   **Code Detail**: The `ReactAdminMessageView` in `predictions/views.py` updates the `reaction` field of the message model, allowing the admin team to visually flag "Approved" (Up) or "Rejected" (Down) appeals.

---

## 📊 Dashboard & Frontend (`templates/`)

### `dashboard.html` & Search Logic
The search bar isn't a simple keyword match; it's a **multi-word intersection search**.
*   **In `predictions/views.py` (`DashboardView`)**: 
    ```python
    def build_multi_word_q(words, field_list):
        # Combined logic matches records containing ALL words (any order) across fields.
    ```
    If you search for "Cow Lumpy", it splits the string into `['Cow', 'Lumpy']` and ensures both words are present in either the animal field or the disease field. This makes the search much more intuitive for users.

### Design Tokens (`base.html`)
The UI uses CSS custom properties (`:root`) for a "Clean Simple Theme."
*   `--primary-color: #2563eb` (Modern Blue)
*   `--main-bg: #f8fafc` (Off-white professional background)
*   **Dynamic Navbar**: Uses Django template logic `{% if user.role == 'doctor' %}` to hide or show the "AI Chat" and "Messages" tabs based on the user's privilege level.

---

## 🛠️ Utility Functions (`utils.py`)
*   **`call_chat_api`**: Implements **Context Management**. To avoid hitting OpenRouter's token limits and to keep the conversation relevant, the code explicitly slices the chat history: `messages = messages[-6:]`. This ensures the AI always remembers the most recent part of the conversation without becoming too expensive or slow.
*   **`generate_ai_report`**: Uses a complex multi-paragraph prompt that instructs the AI to first write in English and then in Urdu, ensuring a "highly structured" output for the farmer.

---

## 🗃️ Database & Models (`predictions/models.py`)
*   **`Report`**: The `authenticated_by` field is a `ManyToManyField`. This allows *multiple* doctors to sign off on a single diagnosis, increasing clinical reliability.
*   **`UserActivity`**: Logs every significant action. In `views.py`, after a report is generated, `UserActivity.objects.create(...)` is called synchronously to ensure a permanent audit trail exists for both students and farm owners.
