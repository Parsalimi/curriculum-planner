from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Course, Curriculum, CurriculumCourse, Prerequisite, RequirementGroup, StudentCourse


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


class CurriculumAdminForm(forms.ModelForm):
    class Meta:
        model = Curriculum
        fields = ("name", "degree", "version", "minimum_credits")
        widgets = {
            "name": forms.TextInput(attrs={"class": "input"}),
            "degree": forms.TextInput(attrs={"class": "input"}),
            "version": forms.TextInput(attrs={"class": "input"}),
            "minimum_credits": forms.NumberInput(attrs={"class": "input"}),
        }


class RequirementGroupAdminForm(forms.ModelForm):
    overflow_to = forms.ModelChoiceField(
        queryset=RequirementGroup.objects.none(),
        required=False,
        empty_label="No overflow destination",
        widget=forms.Select(attrs={"class": "input"}),
    )

    class Meta:
        model = RequirementGroup
        fields = ("name", "type", "required_count", "required_credits", "overflow_to")
        widgets = {
            "name": forms.TextInput(attrs={"class": "input"}),
            "type": forms.Select(attrs={"class": "input"}),
            "required_count": forms.NumberInput(attrs={"class": "input"}),
            "required_credits": forms.NumberInput(attrs={"class": "input"}),
        }

    def __init__(self, *args, curriculum=None, **kwargs):
        super().__init__(*args, **kwargs)
        queryset = RequirementGroup.objects.none()
        if curriculum:
            queryset = RequirementGroup.objects.filter(curriculum=curriculum)
            if self.instance and self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
        self.fields["overflow_to"].queryset = queryset


class CurriculumCourseForm(forms.Form):
    code = forms.CharField(max_length=20, widget=forms.TextInput(attrs={"class": "input"}))
    name = forms.CharField(max_length=200, widget=forms.TextInput(attrs={"class": "input"}))
    credits = forms.IntegerField(min_value=1, widget=forms.NumberInput(attrs={"class": "input"}))
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "input", "rows": 4}),
    )
    is_active = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={"class": "checkbox"}))
    category = forms.ChoiceField(choices=CurriculumCourse.Category.choices, widget=forms.Select(attrs={"class": "input"}))
    recommended_semester = forms.IntegerField(min_value=1, widget=forms.NumberInput(attrs={"class": "input"}))
    is_mandatory = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={"class": "checkbox"}))
    prerequisites = forms.ModelMultipleChoiceField(
        queryset=Course.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "input"}),
    )

    def __init__(self, *args, curriculum=None, curriculum_course=None, **kwargs):
        super().__init__(*args, **kwargs)

        if curriculum:
            queryset = Course.objects.filter(curriculum_courses__curriculum=curriculum).distinct().order_by("code")
            if curriculum_course:
                queryset = queryset.exclude(pk=curriculum_course.course_id)
            self.fields["prerequisites"].queryset = queryset

        if curriculum_course:
            course = curriculum_course.course
            self.fields["code"].initial = course.code
            self.fields["name"].initial = course.name
            self.fields["credits"].initial = course.credits
            self.fields["description"].initial = course.description
            self.fields["is_active"].initial = course.is_active
            self.fields["category"].initial = curriculum_course.category
            self.fields["recommended_semester"].initial = curriculum_course.recommended_semester
            self.fields["is_mandatory"].initial = curriculum_course.is_mandatory
            self.fields["prerequisites"].initial = Course.objects.filter(
                pk__in=course.prerequisites.values_list("prerequisite_id", flat=True)
            )

    def save(self, curriculum, curriculum_course=None):
        code = self.cleaned_data["code"].strip()
        name = self.cleaned_data["name"].strip()

        if curriculum_course:
            course = curriculum_course.course
            course.code = code
            course.name = name
            course.credits = self.cleaned_data["credits"]
            course.description = self.cleaned_data["description"]
            course.is_active = self.cleaned_data["is_active"]
            course.save()
        else:
            course, _ = Course.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "credits": self.cleaned_data["credits"],
                    "description": self.cleaned_data["description"],
                    "is_active": self.cleaned_data["is_active"],
                },
            )
            if course.name != name:
                course.name = name
            if course.credits != self.cleaned_data["credits"]:
                course.credits = self.cleaned_data["credits"]
            if course.description != self.cleaned_data["description"]:
                course.description = self.cleaned_data["description"]
            if course.is_active != self.cleaned_data["is_active"]:
                course.is_active = self.cleaned_data["is_active"]
            course.save()

            curriculum_course = CurriculumCourse.objects.create(
                curriculum=curriculum,
                course=course,
                category=self.cleaned_data["category"],
                recommended_semester=self.cleaned_data["recommended_semester"],
                is_mandatory=self.cleaned_data["is_mandatory"],
            )

        curriculum_course.category = self.cleaned_data["category"]
        curriculum_course.recommended_semester = self.cleaned_data["recommended_semester"]
        curriculum_course.is_mandatory = self.cleaned_data["is_mandatory"]
        curriculum_course.save()

        Prerequisite.objects.filter(course=course).delete()
        for prerequisite in self.cleaned_data["prerequisites"]:
            Prerequisite.objects.get_or_create(
                course=course,
                prerequisite=prerequisite,
            )

        return curriculum_course
