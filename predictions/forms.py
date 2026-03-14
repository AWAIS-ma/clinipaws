from django import forms
from .models import Report, Comment

class ReportForm(forms.ModelForm):
    SYMPTOM_CHOICES = [
    ('', '--- Select Symptom ---'),
    ('abdominal pain - پیٹ میں درد', 'abdominal pain - پیٹ میں درد'),
    ('abdominal swelling - پیٹ کی سوجن', 'abdominal swelling - پیٹ کی سوجن'),
    ('abortion - اسقاط حمل', 'abortion - اسقاط حمل'),
    ('anemia - خون کی کمی', 'anemia - خون کی کمی'),
    ('bloated abdomen - پیٹ پھول جانا', 'bloated abdomen - پیٹ پھول جانا'),
    ('blisters on gums - مسوڑھوں پر چھالے', 'blisters on gums - مسوڑھوں پر چھالے'),
    ('blisters on hooves - کھروں پر چھالے', 'blisters on hooves - کھروں پر چھالے'),
    ('blisters on mouth - منہ میں چھالے', 'blisters on mouth - منہ میں چھالے'),
    ('blisters on tongue - زبان پر چھالے', 'blisters on tongue - زبان پر چھالے'),
    ('bloody discharge - خونی رطوبت', 'bloody discharge - خونی رطوبت'),
    ('chest pain - سینے میں درد', 'chest pain - سینے میں درد'),
    ('convulsions - دورے پڑنا', 'convulsions - دورے پڑنا'),
    ('coughing - کھانسی', 'coughing - کھانسی'),
    ('crackling sound - چرچرانے کی آواز', 'crackling sound - چرچرانے کی آواز'),
    ('crepitation under skin - جلد کے نیچے چرچراہٹ', 'crepitation under skin - جلد کے نیچے چرچراہٹ'),
    ('depression - افسردگی', 'depression - افسردگی'),
    ('diarrhea - اسہال', 'diarrhea - اسہال'),
    ('difficulty breathing - سانس لینے میں دشواری', 'difficulty breathing - سانس لینے میں دشواری'),
    ('difficulty walking - چلنے میں دشواری', 'difficulty walking - چلنے میں دشواری'),
    ('distress - کرب یا پریشانی', 'distress - کرب یا پریشانی'),
    ('drooling - منہ سے رال ٹپکنا', 'drooling - منہ سے رال ٹپکنا'),
    ('enlarged lymph nodes - لمف غدود کا بڑھ جانا', 'enlarged lymph nodes - لمف غدود کا بڑھ جانا'),
    ('excessive salivation - زیادہ لعاب آنا', 'excessive salivation - زیادہ لعاب آنا'),
    ('fatigue - تھکن', 'fatigue - تھکن'),
    ('fever - بخار', 'fever - بخار'),
    ('high fever - تیز بخار', 'high fever - تیز بخار'),
    ('high temperature - زیادہ درجہ حرارت', 'high temperature - زیادہ درجہ حرارت'),
    ('infertility - بانجھ پن', 'infertility - بانجھ پن'),
    ('kicking abdomen - پیٹ پر لات مارنا', 'kicking abdomen - پیٹ پر لات مارنا'),
    ('lameness - لنگڑاپن', 'lameness - لنگڑاپن'),
    ('lesions on skin - جلد پر زخم', 'lesions on skin - جلد پر زخم'),
    ('loss of appetite - بھوک میں کمی', 'loss of appetite - بھوک میں کمی'),
    ('milk clots - دودھ میں جماؤ', 'milk clots - دودھ میں جماؤ'),
    ('nasal discharge - ناک سے رطوبت آنا', 'nasal discharge - ناک سے رطوبت آنا'),
    ('painful udder - تھنی میں درد', 'painful udder - تھنی میں درد'),
    ('pale mucous membranes - زرد بلغم والی جھلیاں', 'pale mucous membranes - زرد بلغم والی جھلیاں'),
    ('painless lumps - بغیر درد والی گانٹھیں', 'painless lumps - بغیر درد والی گانٹھیں'),
    ('rapid breathing - تیز سانس لینا', 'rapid breathing - تیز سانس لینا'),
    ('reduced milk production - دودھ کی پیداوار میں کمی', 'reduced milk production - دودھ کی پیداوار میں کمی'),
    ('reduced movement - حرکت میں کمی', 'reduced movement - حرکت میں کمی'),
    ('reduced milk yield - دودھ کی پیداوار میں کمی', 'reduced milk yield - دودھ کی پیداوار میں کمی'),
    ('restlessness - بے چینی', 'restlessness - بے چینی'),
    ('retained placenta - نالی کا برقرار رہنا', 'retained placenta - نالی کا برقرار رہنا'),
    ('rough coat - کھردرا بال', 'rough coat - کھردرا بال'),
    ('salivation - لعاب دہن کا زیادہ اخراج', 'salivation - لعاب دہن کا زیادہ اخراج'),
    ('scabs on muzzle - منہ کے اردگرد خراشیں', 'scabs on muzzle - منہ کے اردگرد خراشیں'),
    ('scratching - خارش کرنا', 'scratching - خارش کرنا'),
    ('skin nodules - جلد پر گلٹیاں', 'skin nodules - جلد پر گلٹیاں'),
    ('slow growth - نشوونما میں کمی', 'slow growth - نشوونما میں کمی'),
    ('sores on gums - مسوڑھوں پر زخم', 'sores on gums - مسوڑھوں پر زخم'),
    ('sores on hooves - کھروں پر زخم', 'sores on hooves - کھروں پر زخم'),
    ('sores on mouth - منہ پر زخم', 'sores on mouth - منہ پر زخم'),
    ('sores on tongue - زبان پر زخم', 'sores on tongue - زبان پر زخم'),
    ('sudden death - اچانک موت', 'sudden death - اچانک موت'),
    ('swelling in limb - بازو یا ٹانگ میں سوجن', 'swelling in limb - بازو یا ٹانگ میں سوجن'),
    ('swelling in muscle - پٹھوں میں سوجن', 'swelling in muscle - پٹھوں میں سوجن'),
    ('swelling in muscles - پٹھوں میں سوجن', 'swelling in muscles - پٹھوں میں سوجن'),
    ('swelling in neck - گردن میں سوجن', 'swelling in neck - گردن میں سوجن'),
    ('swollen joints - سوجے ہوئے جوڑ', 'swollen joints - سوجے ہوئے جوڑ'),
    ('swollen limbs - سوجے ہوئے اعضاء', 'swollen limbs - سوجے ہوئے اعضاء'),
    ('trembling - لرزش', 'trembling - لرزش'),
    ('udder redness - تھنی کی سرخی', 'udder redness - تھنی کی سرخی'),
    ('watering eyes - آنکھوں سے پانی آنا', 'watering eyes - آنکھوں سے پانی آنا'),
    ('weakness - کمزوری', 'weakness - کمزوری'),
    ('weight loss - وزن میں کمی', 'weight loss - وزن میں کمی'),
]

   

    symptom1 = forms.ChoiceField(
        choices=SYMPTOM_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    symptom2 = forms.ChoiceField(
        choices=SYMPTOM_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    symptom3 = forms.ChoiceField(
        choices=SYMPTOM_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Report
        fields = ['animal', 'symptom1', 'symptom2', 'symptom3']
        widgets = {
            'animal': forms.Select(attrs={'class': 'form-control'}),
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Add your medical opinion or advice here...'
            }),
        }

class ImageReportForm(forms.ModelForm):
    """Form for image-based disease detection"""
    class Meta:
        from .models import ImageReport
        model = ImageReport
        fields = ['animal', 'original_image']
        widgets = {
            'animal': forms.Select(attrs={'class': 'form-control'}),
            'original_image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
        }

class ImageCommentForm(forms.ModelForm):
    """Form for adding comments to image reports"""
    class Meta:
        from .models import ImageComment
        model = ImageComment
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Add your medical opinion or advice here...'
            }),
        }
