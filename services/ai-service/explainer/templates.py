"""
ai-service/explainer/templates.py

Template-based plain-language explanations for common lab tests.
One entry per test_name (canonical, matching parsers/patterns.py).

TONE RULES (01_PROJECT_CONTEXT.md §4, non-negotiable):
  - Never state "you have X condition" or "you are diagnosed with X".
  - Frame as "commonly associated with", "may be worth discussing".
  - Always frame relative to the reference range on file.
  - Never use the word "abnormal" without qualifying that a single out-of-range
    value is not a diagnosis.

Each TestInfo entry has:
  - what_it_is_en / _hi: one sentence explaining what the test measures.
  - high_note_en / _hi: plain-language context for above-range values.
  - low_note_en / _hi: plain-language context for below-range values.
  - normal_note_en / _hi: reassurance for in-range values.

Hindi translations are natural (not machine-translated) and reviewed for
medical accuracy. Do not add tests here without both EN and HI content.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TestInfo:
    what_it_is_en: str
    what_it_is_hi: str
    normal_note_en: str
    normal_note_hi: str
    high_note_en: str
    high_note_hi: str
    low_note_en: str
    low_note_hi: str


TEST_INFO: dict[str, TestInfo] = {
    "Haemoglobin": TestInfo(
        what_it_is_en="Haemoglobin is the protein in red blood cells that carries oxygen around the body.",
        what_it_is_hi="हीमोग्लोबिन लाल रक्त कोशिकाओं में एक प्रोटीन है जो शरीर में ऑक्सीजन ले जाता है।",
        normal_note_en="Your haemoglobin level is within the typical reference range, which generally suggests adequate oxygen-carrying capacity.",
        normal_note_hi="आपका हीमोग्लोबिन स्तर सामान्य संदर्भ सीमा के भीतर है, जो आमतौर पर पर्याप्त ऑक्सीजन-वहन क्षमता का संकेत देता है।",
        high_note_en="A haemoglobin level above the reference range can sometimes be associated with dehydration, lung conditions, or other factors. It may be worth discussing with your doctor.",
        high_note_hi="संदर्भ सीमा से अधिक हीमोग्लोबिन कभी-कभी निर्जलीकरण, फेफड़ों की स्थिति या अन्य कारकों से जुड़ा हो सकता है। इस बारे में अपने डॉक्टर से चर्चा करना उचित हो सकता है।",
        low_note_en="A haemoglobin level below the reference range is commonly associated with anaemia, which can have several causes including iron or vitamin deficiency. This is worth discussing with your doctor.",
        low_note_hi="संदर्भ सीमा से कम हीमोग्लोबिन सामान्यतः एनीमिया से जुड़ा होता है, जिसके कई कारण हो सकते हैं जैसे आयरन या विटामिन की कमी। इस बारे में अपने डॉक्टर से बात करना उचित है।",
    ),
    "WBC": TestInfo(
        what_it_is_en="White blood cells (WBC) are part of the immune system and help the body fight infections.",
        what_it_is_hi="श्वेत रक्त कोशिकाएं (WBC) प्रतिरक्षा प्रणाली का हिस्सा हैं और शरीर को संक्रमण से लड़ने में मदद करती हैं।",
        normal_note_en="Your WBC count is within the typical reference range, suggesting your immune system activity is broadly normal.",
        normal_note_hi="आपकी WBC गिनती सामान्य संदर्भ सीमा के भीतर है, जो आपकी प्रतिरक्षा प्रणाली की सामान्य गतिविधि का संकेत देती है।",
        high_note_en="A WBC count above the reference range can be associated with infection, inflammation, or other conditions. A single elevated count should be interpreted in context by your doctor.",
        high_note_hi="संदर्भ सीमा से अधिक WBC गिनती संक्रमण, सूजन या अन्य स्थितियों से जुड़ी हो सकती है। एक बार के बढ़े हुए स्तर की व्याख्या आपके डॉक्टर से संदर्भ में करानी चाहिए।",
        low_note_en="A WBC count below the reference range may be associated with certain infections, medication effects, or bone marrow conditions. It is worth discussing with your doctor.",
        low_note_hi="संदर्भ सीमा से कम WBC गिनती कुछ संक्रमणों, दवाओं के प्रभाव या अस्थि मज्जा की स्थितियों से जुड़ी हो सकती है। इसे अपने डॉक्टर से चर्चा करना उचित है।",
    ),
    "Platelets": TestInfo(
        what_it_is_en="Platelets are small blood cells that help blood clot when you have a cut or injury.",
        what_it_is_hi="प्लेटलेट्स छोटी रक्त कोशिकाएं हैं जो कटने या चोट लगने पर रक्त को जमाने में मदद करती हैं।",
        normal_note_en="Your platelet count is within the typical reference range.",
        normal_note_hi="आपकी प्लेटलेट गिनती सामान्य संदर्भ सीमा के भीतर है।",
        high_note_en="A platelet count above the reference range can be associated with certain inflammatory conditions or other factors. This may be worth discussing with your doctor.",
        high_note_hi="संदर्भ सीमा से अधिक प्लेटलेट गिनती कुछ सूजन संबंधी स्थितियों या अन्य कारकों से जुड़ी हो सकती है। इसे अपने डॉक्टर से चर्चा करना उचित हो सकता है।",
        low_note_en="A platelet count below the reference range can be associated with a reduced ability to form clots. This is worth discussing promptly with your doctor.",
        low_note_hi="संदर्भ सीमा से कम प्लेटलेट गिनती थक्का बनाने की कम क्षमता से जुड़ी हो सकती है। इसे शीघ्र अपने डॉक्टर से चर्चा करना उचित है।",
    ),
    "Total Cholesterol": TestInfo(
        what_it_is_en="Total cholesterol is the overall level of cholesterol in your blood, including both 'good' (HDL) and 'bad' (LDL) types.",
        what_it_is_hi="कुल कोलेस्ट्रॉल आपके रक्त में कोलेस्ट्रॉल का कुल स्तर है, जिसमें 'अच्छा' (HDL) और 'बुरा' (LDL) दोनों प्रकार शामिल हैं।",
        normal_note_en="Your total cholesterol is within the typical reference range.",
        normal_note_hi="आपका कुल कोलेस्ट्रॉल सामान्य संदर्भ सीमा के भीतर है।",
        high_note_en="A total cholesterol level above the reference range is commonly associated with increased cardiovascular risk over time. Diet, exercise, and other factors all play a role. This is worth discussing with your doctor, especially alongside your LDL and HDL levels.",
        high_note_hi="संदर्भ सीमा से अधिक कुल कोलेस्ट्रॉल समय के साथ बढ़े हुए हृदय रोग के जोखिम से जुड़ा हो सकता है। आहार, व्यायाम और अन्य कारक भी महत्वपूर्ण हैं। इसे अपने LDL और HDL स्तरों के साथ अपने डॉक्टर से चर्चा करना उचित है।",
        low_note_en="Total cholesterol below the reference range is less common and may be worth discussing with your doctor in context of your full lipid panel.",
        low_note_hi="संदर्भ सीमा से कम कुल कोलेस्ट्रॉल कम सामान्य है और आपके पूरे लिपिड पैनल के संदर्भ में अपने डॉक्टर से चर्चा करना उचित हो सकता है।",
    ),
    "LDL Cholesterol": TestInfo(
        what_it_is_en="LDL cholesterol ('bad' cholesterol) can build up in artery walls if elevated over time.",
        what_it_is_hi="LDL कोलेस्ट्रॉल ('खराब' कोलेस्ट्रॉल) यदि लंबे समय तक अधिक हो तो धमनियों की दीवारों में जमा हो सकता है।",
        normal_note_en="Your LDL cholesterol is within the typical reference range.",
        normal_note_hi="आपका LDL कोलेस्ट्रॉल सामान्य संदर्भ सीमा के भीतर है।",
        high_note_en="An LDL level above the reference range is commonly associated with higher cardiovascular risk over time. Lifestyle factors (diet, exercise) and genetics both play a role. This is worth discussing with your doctor.",
        high_note_hi="संदर्भ सीमा से अधिक LDL स्तर समय के साथ अधिक हृदय रोग जोखिम से जुड़ा हो सकता है। जीवनशैली के कारक (आहार, व्यायाम) और आनुवंशिकी दोनों महत्वपूर्ण हैं। इसे अपने डॉक्टर से चर्चा करना उचित है।",
        low_note_en="LDL below the reference range is generally considered favourable for cardiovascular health.",
        low_note_hi="संदर्भ सीमा से कम LDL आमतौर पर हृदय स्वास्थ्य के लिए अनुकूल माना जाता है।",
    ),
    "HDL Cholesterol": TestInfo(
        what_it_is_en="HDL cholesterol ('good' cholesterol) helps remove other forms of cholesterol from the bloodstream.",
        what_it_is_hi="HDL कोलेस्ट्रॉल ('अच्छा' कोलेस्ट्रॉल) रक्त प्रवाह से अन्य प्रकार के कोलेस्ट्रॉल को हटाने में मदद करता है।",
        normal_note_en="Your HDL cholesterol is within the typical reference range.",
        normal_note_hi="आपका HDL कोलेस्ट्रॉल सामान्य संदर्भ सीमा के भीतर है।",
        high_note_en="A high HDL level is generally considered protective for cardiovascular health.",
        high_note_hi="अधिक HDL स्तर आमतौर पर हृदय स्वास्थ्य के लिए सुरक्षात्मक माना जाता है।",
        low_note_en="A low HDL level is commonly associated with higher cardiovascular risk. Regular exercise and diet changes can help improve HDL levels. This may be worth discussing with your doctor.",
        low_note_hi="कम HDL स्तर अधिक हृदय रोग जोखिम से जुड़ा हो सकता है। नियमित व्यायाम और आहार परिवर्तन HDL स्तर सुधारने में मदद कर सकते हैं। इसे अपने डॉक्टर से चर्चा करना उचित हो सकता है।",
    ),
    "Triglycerides": TestInfo(
        what_it_is_en="Triglycerides are a type of fat in the blood. High levels are often associated with diet, alcohol intake, or other metabolic factors.",
        what_it_is_hi="ट्राइग्लिसराइड्स रक्त में एक प्रकार की वसा हैं। उच्च स्तर अक्सर आहार, शराब सेवन या अन्य चयापचय कारकों से जुड़े होते हैं।",
        normal_note_en="Your triglyceride level is within the typical reference range.",
        normal_note_hi="आपका ट्राइग्लिसराइड स्तर सामान्य संदर्भ सीमा के भीतर है।",
        high_note_en="Elevated triglycerides are commonly associated with diet (high sugar/refined carbohydrate intake), alcohol, and metabolic conditions. This is worth discussing with your doctor alongside your full lipid panel.",
        high_note_hi="ऊंचे ट्राइग्लिसराइड्स आमतौर पर आहार (अधिक चीनी/परिष्कृत कार्बोहाइड्रेट), शराब और चयापचय स्थितियों से जुड़े होते हैं। अपने पूरे लिपिड पैनल के साथ इसे डॉक्टर से चर्चा करना उचित है।",
        low_note_en="Low triglycerides are generally not a concern.",
        low_note_hi="कम ट्राइग्लिसराइड्स आमतौर पर चिंता का विषय नहीं हैं।",
    ),
    "TSH": TestInfo(
        what_it_is_en="TSH (thyroid-stimulating hormone) is produced by the pituitary gland and regulates thyroid function. It is the primary screening test for thyroid disorders.",
        what_it_is_hi="TSH (थायरॉइड-उत्तेजक हार्मोन) पिट्यूटरी ग्रंथि द्वारा उत्पादित होता है और थायरॉइड कार्य को नियंत्रित करता है। यह थायरॉइड विकारों के लिए प्राथमिक स्क्रीनिंग परीक्षण है।",
        normal_note_en="Your TSH level is within the typical reference range, which generally suggests the thyroid is being stimulated appropriately.",
        normal_note_hi="आपका TSH स्तर सामान्य संदर्भ सीमा के भीतर है, जो आमतौर पर यह सुझाता है कि थायरॉइड उचित रूप से उत्तेजित हो रहा है।",
        high_note_en="A TSH level above the reference range can be associated with an underactive thyroid (hypothyroidism). This should be interpreted alongside Free T4 and in discussion with your doctor.",
        high_note_hi="संदर्भ सीमा से अधिक TSH एक कम सक्रिय थायरॉइड (हाइपोथायरायडिज्म) से जुड़ा हो सकता है। इसे Free T4 के साथ और अपने डॉक्टर से चर्चा में समझना चाहिए।",
        low_note_en="A TSH level below the reference range can be associated with an overactive thyroid (hyperthyroidism). This should be interpreted alongside Free T4 and in discussion with your doctor.",
        low_note_hi="संदर्भ सीमा से कम TSH एक अधिक सक्रिय थायरॉइड (हाइपरथायरायडिज्म) से जुड़ा हो सकता है। इसे Free T4 के साथ और अपने डॉक्टर से चर्चा में समझना चाहिए।",
    ),
    "HbA1c": TestInfo(
        what_it_is_en="HbA1c (glycated haemoglobin) reflects your average blood sugar level over the past 2–3 months. It is used to monitor blood glucose control over time.",
        what_it_is_hi="HbA1c (ग्लाइकेटेड हीमोग्लोबिन) पिछले 2-3 महीनों में आपके औसत रक्त शर्करा स्तर को दर्शाता है। इसका उपयोग समय के साथ रक्त ग्लूकोज नियंत्रण की निगरानी के लिए किया जाता है।",
        normal_note_en="Your HbA1c is within the typical reference range, which generally suggests average blood glucose has been well-controlled over the past 2–3 months.",
        normal_note_hi="आपका HbA1c सामान्य संदर्भ सीमा के भीतर है, जो आमतौर पर यह सुझाता है कि पिछले 2-3 महीनों में औसत रक्त ग्लूकोज अच्छी तरह नियंत्रित रहा है।",
        high_note_en="An HbA1c above the reference range indicates average blood glucose has been higher than typical over the past 2–3 months. This may be worth discussing with your doctor alongside fasting glucose and other context.",
        high_note_hi="संदर्भ सीमा से अधिक HbA1c इंगित करता है कि पिछले 2-3 महीनों में औसत रक्त ग्लूकोज सामान्य से अधिक रहा है। इसे फास्टिंग ग्लूकोज और अन्य संदर्भ के साथ अपने डॉक्टर से चर्चा करना उचित हो सकता है।",
        low_note_en="An HbA1c below the typical reference range is uncommon and may be worth discussing with your doctor.",
        low_note_hi="सामान्य संदर्भ सीमा से कम HbA1c असामान्य है और अपने डॉक्टर से चर्चा करना उचित हो सकता है।",
    ),
}

# Fallback for tests not in TEST_INFO
_FALLBACK = TestInfo(
    what_it_is_en="This test measures a specific marker in your blood.",
    what_it_is_hi="यह परीक्षण आपके रक्त में एक विशिष्ट मार्कर को मापता है।",
    normal_note_en="Your result is within the typical reference range.",
    normal_note_hi="आपका परिणाम सामान्य संदर्भ सीमा के भीतर है।",
    high_note_en="Your result is above the typical reference range. This may be worth discussing with your doctor.",
    high_note_hi="आपका परिणाम सामान्य संदर्भ सीमा से अधिक है। इसे अपने डॉक्टर से चर्चा करना उचित हो सकता है।",
    low_note_en="Your result is below the typical reference range. This may be worth discussing with your doctor.",
    low_note_hi="आपका परिणाम सामान्य संदर्भ सीमा से कम है। इसे अपने डॉक्टर से चर्चा करना उचित हो सकता है।",
)
