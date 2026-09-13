from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Curriculum, StudentCourse


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")


class CourseStatusForm(forms.ModelForm):
    class Meta:
        model = StudentCourse
        fields = ("status", "grade")
        widgets = {
            "status": forms.Select(attrs={"class": "input"}),
            "grade": forms.NumberInput(
                attrs={
                    "class": "input",
                    "step": "0.01",
                    "min": "0",
                    "max": "20",
                    "placeholder": "e.g. 18.50",
                }
            ),
        }


class CurriculumSelectForm(forms.Form):
    curriculum = forms.ModelChoiceField(
        queryset=Curriculum.objects.all(),
        empty_label="Choose a curriculum",
        widget=forms.Select(attrs={"class": "input"}),
    )
