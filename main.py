import ddddocr

ocr = ddddocr.DdddOcr()

with open("captcha.png", "rb") as f:
    img = f.read()

code = ocr.classification(img)
print("Код капчи:", code)
# здесь сразу подставляешь code в запрос/форму
