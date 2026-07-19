// ============================================================
//  명함 스캔 챗봇 - Google Apps Script 버전
//  텔레그램 웹훅 → Gemini OCR → Gmail 발송 → Sheets 저장
// ============================================================

// ▼ 여기에 본인 설정값을 입력하세요
var CONFIG = {
  TELEGRAM_TOKEN:   PropertiesService.getScriptProperties().getProperty("TELEGRAM_TOKEN"),
  GEMINI_API_KEY:   PropertiesService.getScriptProperties().getProperty("GEMINI_API_KEY"),
  MY_EMAIL:         PropertiesService.getScriptProperties().getProperty("MY_EMAIL"),          // 내 Gmail 주소
  MY_CARD_FILE_ID:  PropertiesService.getScriptProperties().getProperty("MY_CARD_FILE_ID"),   // Google Drive 명함 이미지 파일 ID
  EMAIL_INTRO:      PropertiesService.getScriptProperties().getProperty("EMAIL_INTRO") || "안녕하세요! 오늘 명함을 교환했습니다. 제 명함을 첨부 드립니다.",
  SHEET_ID:         PropertiesService.getScriptProperties().getProperty("SHEET_ID"),          // Google Sheets ID (선택)
};

var TELEGRAM_API = "https://api.telegram.org/bot" + CONFIG.TELEGRAM_TOKEN;

// ============================================================
//  텔레그램 웹훅 진입점
// ============================================================
function doPost(e) {
  try {
    var update = JSON.parse(e.postData.contents);
    handleUpdate(update);
  } catch (err) {
    Logger.log("doPost 오류: " + err);
  }
  return ContentService.createTextOutput(JSON.stringify({status: "ok"})).setMimeType(ContentService.MimeType.JSON);
}

function handleUpdate(update) {
  // 일반 메시지 (사진 포함)
  if (update.message) {
    var msg = update.message;
    var chatId = msg.chat.id;

    if (msg.text === "/start") {
      sendMessage(chatId,
        "안녕하세요! 명함 스캔 봇입니다.\n\n" +
        "명함 사진을 전송해 주시면:\n" +
        "1️⃣ 명함 정보를 자동으로 인식합니다\n" +
        "2️⃣ 명함에 적힌 이메일로 제 명함을 발송합니다\n\n" +
        "📷 명함 사진을 보내주세요!"
      );
      return;
    }

    if (msg.photo) {
      handlePhoto(chatId, msg);
      return;
    }
  }

  // 인라인 버튼 콜백 (확인/취소)
  if (update.callback_query) {
    handleCallback(update.callback_query);
  }
}

// ============================================================
//  사진 처리
// ============================================================
function handlePhoto(chatId, msg) {
  sendMessage(chatId, "📷 명함을 분석 중입니다... 잠시만 기다려주세요.");

  // 가장 고해상도 사진의 file_id 가져오기
  var photos = msg.photo;
  var fileId = photos[photos.length - 1].file_id;
  Logger.log("1. file_id: " + fileId);

  // 텔레그램에서 이미지 URL 획득
  var fileUrl = getTelegramFileUrl(fileId);
  Logger.log("2. fileUrl: " + fileUrl);
  if (!fileUrl) {
    sendMessage(chatId, "❌ 이미지를 가져오지 못했습니다. 다시 시도해 주세요.");
    return;
  }

  // 이미지 데이터를 base64로 변환
  var imageBase64 = fetchImageAsBase64(fileUrl);
  Logger.log("3. imageBase64 길이: " + (imageBase64 ? imageBase64.length : "null"));
  if (!imageBase64) {
    sendMessage(chatId, "❌ 이미지 다운로드에 실패했습니다.");
    return;
  }

  // Gemini OCR
  var cardInfo;
  try {
    cardInfo = extractCardInfo(imageBase64);
    Logger.log("4. OCR 결과: " + JSON.stringify(cardInfo));
  } catch (err) {
    Logger.log("OCR 오류: " + err);
    sendMessage(chatId, "❌ 명함 인식에 실패했습니다. 오류: " + err);
    return;
  }

  if (!cardInfo.email) {
    sendMessage(chatId, "⚠️ 이메일 주소를 인식하지 못했습니다.\n선명한 사진으로 다시 시도해 주세요.");
    return;
  }

  // 임시 저장 (Script Properties 사용 - 메모리 대신)
  PropertiesService.getScriptProperties().setProperty(
    "pending_" + chatId,
    JSON.stringify(cardInfo)
  );

  // 확인 메시지 + 버튼
  var text =
    "📋 인식된 명함 정보:\n\n" +
    "👤 이름: " + (cardInfo.name || "-") + "\n" +
    "🏢 회사: " + (cardInfo.company || "-") + "\n" +
    "💼 직책: " + (cardInfo.title || "-") + "\n" +
    "📧 이메일: " + (cardInfo.email || "-") + "\n" +
    "📞 전화번호: " + (cardInfo.phone || "-") + "\n" +
    "📍 주소: " + (cardInfo.address || "-") + "\n\n" +
    "위 정보로 이메일을 발송할까요?";

  var keyboard = {
    inline_keyboard: [[
      { text: "✅ 확인 후 발송", callback_data: "confirm" },
      { text: "❌ 취소",        callback_data: "cancel"  }
    ]]
  };

  sendMessage(chatId, text, keyboard);
}

// ============================================================
//  버튼 콜백 처리
// ============================================================
function handleCallback(query) {
  var chatId   = query.message.chat.id;
  var msgId    = query.message.message_id;
  var callbackId = query.id;

  // 버튼 응답 (로딩 스피너 제거)
  answerCallbackQuery(callbackId);

  if (query.data === "cancel") {
    PropertiesService.getScriptProperties().deleteProperty("pending_" + chatId);
    editMessage(chatId, msgId, "❌ 취소되었습니다.");
    return;
  }

  if (query.data !== "confirm") return;

  var raw = PropertiesService.getScriptProperties().getProperty("pending_" + chatId);
  if (!raw) {
    editMessage(chatId, msgId, "⚠️ 세션이 만료되었습니다. 다시 사진을 보내주세요.");
    return;
  }

  var cardInfo = JSON.parse(raw);
  PropertiesService.getScriptProperties().deleteProperty("pending_" + chatId);

  editMessage(chatId, msgId, "⏳ 이메일 발송 및 저장 처리 중...");

  // 이메일 발송
  var emailSent = false;
  try {
    sendMyCard(cardInfo.email, cardInfo.name || "");
    emailSent = true;
  } catch (err) {
    Logger.log("이메일 오류: " + err);
    sendMessage(chatId, "❌ 이메일 발송에 실패했습니다. Gmail 설정을 확인해 주세요.");
  }

  // Sheets 저장 (SHEET_ID 설정된 경우만)
  if (CONFIG.SHEET_ID) {
    try {
      saveToSheet(cardInfo, emailSent);
    } catch (err) {
      Logger.log("Sheets 저장 오류: " + err);
    }
  }

  if (emailSent) {
    sendMessage(chatId, "✅ 처리 완료!\n📧 이메일 발송: 성공");
  }
}

// ============================================================
//  Gemini OCR
// ============================================================
function extractCardInfo(imageBase64) {
  var url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key=" + CONFIG.GEMINI_API_KEY;

  var prompt =
    "이 명함 이미지에서 다음 정보를 추출해 주세요.\n" +
    "반드시 아래 JSON 형식으로만 응답하고, 다른 텍스트는 포함하지 마세요.\n\n" +
    "{\n" +
    '  "name": "이름",\n' +
    '  "company": "회사명",\n' +
    '  "title": "직책",\n' +
    '  "email": "이메일주소",\n' +
    '  "phone": "전화번호",\n' +
    '  "address": "주소"\n' +
    "}\n\n" +
    "정보가 없으면 해당 필드를 빈 문자열(\"\")로 채워주세요.";

  var payload = {
    contents: [{
      parts: [
        { text: prompt },
        { inline_data: { mime_type: "image/jpeg", data: imageBase64 } }
      ]
    }]
  };

  var response = UrlFetchApp.fetch(url, {
    method: "POST",
    contentType: "application/json",
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  });

  var result = JSON.parse(response.getContentText());
  var raw = result.candidates[0].content.parts[0].text.trim();

  // ```json ... ``` 제거
  raw = raw.replace(/```json\n?/g, "").replace(/```\n?/g, "").trim();

  return JSON.parse(raw);
}

// ============================================================
//  Gmail 이메일 발송
// ============================================================
function sendMyCard(toEmail, recipientName) {
  var subject = "명함을 전달 드립니다";
  var body    = CONFIG.EMAIL_INTRO;

  var options = { name: CONFIG.MY_EMAIL };

  // Google Drive에 저장된 내 명함 이미지 첨부
  if (CONFIG.MY_CARD_FILE_ID) {
    var file = DriveApp.getFileById(CONFIG.MY_CARD_FILE_ID);
    options.attachments = [file.getAs(MimeType.JPEG)];
  }

  GmailApp.sendEmail(toEmail, subject, body, options);
}

// ============================================================
//  Google Sheets 저장
// ============================================================
function saveToSheet(cardInfo, emailSent) {
  var sheet = SpreadsheetApp.openById(CONFIG.SHEET_ID).getActiveSheet();
  var now   = Utilities.formatDate(new Date(), "Asia/Seoul", "yyyy-MM-dd HH:mm");

  sheet.appendRow([
    cardInfo.name    || "",
    cardInfo.company || "",
    cardInfo.title   || "",
    cardInfo.email   || "",
    cardInfo.phone   || "",
    now,
    emailSent ? "성공" : "실패"
  ]);
}

// 최초 1회 헤더 설정
function setupSheetHeader() {
  var sheet = SpreadsheetApp.openById(CONFIG.SHEET_ID).getActiveSheet();
  sheet.getRange("A1:G1").setValues([["이름", "회사", "직책", "이메일", "전화번호", "등록일시", "발송여부"]]);
}

// ============================================================
//  텔레그램 API 헬퍼
// ============================================================
function getTelegramFileUrl(fileId) {
  var res = UrlFetchApp.fetch(TELEGRAM_API + "/getFile?file_id=" + fileId, { muteHttpExceptions: true });
  var data = JSON.parse(res.getContentText());
  if (!data.ok) return null;
  return "https://api.telegram.org/file/bot" + CONFIG.TELEGRAM_TOKEN + "/" + data.result.file_path;
}

function fetchImageAsBase64(url) {
  var res = UrlFetchApp.fetch(url, { muteHttpExceptions: true });
  if (res.getResponseCode() !== 200) return null;
  return Utilities.base64Encode(res.getContent());
}

function sendMessage(chatId, text, replyMarkup) {
  var payload = { chat_id: chatId, text: text };
  if (replyMarkup) payload.reply_markup = JSON.stringify(replyMarkup);
  UrlFetchApp.fetch(TELEGRAM_API + "/sendMessage", {
    method: "POST",
    contentType: "application/json",
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  });
}

function editMessage(chatId, msgId, text) {
  UrlFetchApp.fetch(TELEGRAM_API + "/editMessageText", {
    method: "POST",
    contentType: "application/json",
    payload: JSON.stringify({ chat_id: chatId, message_id: msgId, text: text }),
    muteHttpExceptions: true
  });
}

function answerCallbackQuery(callbackId) {
  UrlFetchApp.fetch(TELEGRAM_API + "/answerCallbackQuery", {
    method: "POST",
    contentType: "application/json",
    payload: JSON.stringify({ callback_query_id: callbackId }),
    muteHttpExceptions: true
  });
}

// ============================================================
//  웹훅 등록 (최초 1회 실행)
// ============================================================
function registerWebhook() {
  var webAppUrl = "여기에_웹앱_URL_붙여넣기"; // 배포 후 나오는 URL

  // 실제 리다이렉트 URL 찾기
  var res = UrlFetchApp.fetch(webAppUrl, {
    method: "POST",
    contentType: "application/json",
    payload: JSON.stringify({test: true}),
    followRedirects: false,
    muteHttpExceptions: true
  });
  var realUrl = res.getHeaders()["Location"];
  if (realUrl) {
    Logger.log("실제 URL: " + realUrl);
    webAppUrl = realUrl;
  }

  var result = UrlFetchApp.fetch(
    TELEGRAM_API + "/setWebhook?url=" + encodeURIComponent(webAppUrl),
    { muteHttpExceptions: true }
  );
  Logger.log(result.getContentText());
}
