# Zoom Real-time Translator (Python)

โปรแกรมตัวอย่างสำหรับถอดเสียงภาษาอังกฤษจากเสียง Zoom แล้วแปลเป็นภาษาไทยแบบเรียลไทม์ โดยไม่ต้องใช้ OpenAI API key

## คุณสมบัติ
- บันทึกเสียงจากอุปกรณ์เสียง Windows
- ถอดเสียงภาษาอังกฤษแบบเรียลไทม์ด้วย Vosk แบบ offline/streaming
- แสดงผลข้อความอังกฤษทันทีขณะพูด
- แปลผลเป็นภาษาไทยหลังได้คำอังกฤษแล้ว
- แสดงผลด้านซ้ายเป็นข้อความภาษาอังกฤษ และด้านขวาเป็นคำแปลภาษาไทย

## สิ่งที่ต้องเตรียม
1. ติดตั้ง Python 3.11 หรือใหม่กว่า
2. ดาวน์โหลดโมเดล Vosk ภาษาอังกฤษ และวางไว้ในโฟลเดอร์ `model` ภายในโฟลเดอร์โปรเจกต์
   - ตัวอย่าง model เล็ก: https://alphacephei.com/vosk/models
   - สำหรับภาษาไทย ให้วางโมเดลไว้ในโฟลเดอร์ `model-th\model` หรือกำหนดค่า environment variable `VOSK_MODEL_PATH_TH`
     ```powershell
     setx VOSK_MODEL_PATH_TH "c:\Users\Panda_X\Downloads\Captions\model-th\model"
     ```
   - หากต้องการเก็บโมเดลไว้ที่อื่น ให้ตั้งค่า environment variable `VOSK_MODEL_PATH` สำหรับค่าเริ่มต้นทั่วไป
     ```powershell
     setx VOSK_MODEL_PATH "c:\Users\Panda_X\Downloads\Captions\model"
     ```
3. ลงไลบรารี:
```bash
pip install -r requirements.txt
```

## การใช้งาน
1. เปิด Zoom และตั้งค่าอุปกรณ์เสียง Windows ให้สามารถ "จับเสียงจากลำโพง" ได้ เช่น Stereo Mix หรือ Virtual Audio Cable
2. รันโปรแกรม:
```bash
python main.py
```
3. เลือกอุปกรณ์รับเสียงจากเมนู `Input Device`
4. กดปุ่ม `Start`
5. โปรแกรมจะรับเสียงต่อเนื่องแบบ streaming แล้วแสดงข้อความภาษาอังกฤษทันที
6. คำแปลภาษาไทยจะตามมาทีหลังโดยอัตโนมัติ
7. หากต้องการบันทึกผล ให้กดปุ่ม `Save`
8. หากต้องการล้างผล ให้กดปุ่ม `Clear`

## สร้างไฟล์ `.exe`
บน Windows ให้ใช้ PyInstaller:
```bash
python -m PyInstaller --onefile --windowed main.py
```
ไฟล์จะอยู่ในโฟลเดอร์ `dist\main.exe`

## หมายเหตุ
- โปรแกรมนี้สามารถถอดเสียงภาษาอังกฤษแบบ offline ด้วย Vosk ได้โดยไม่ต้องใช้ OpenAI API key
- การแปลเป็นภาษาไทยยังใช้ Google Translate ผ่าน `googletrans` ซึ่งต้องเชื่อมต่ออินเทอร์เน็ต แต่ไม่จำเป็นต้องมี API key
- หากต้องการจับเสียง Zoom โดยตรง ให้เลือกอุปกรณ์เสียงที่เป็น loopback หรือ Stereo Mix ใน Windows Sound settings
"# Captions" 
