from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from .models import Domain, Question, Exam, Result, Profile

@admin.register(Question)
class QuestionAdmin(ImportExportModelAdmin):
    list_display = ('question_text', 'domain')

admin.site.register(Domain)
admin.site.register(Exam)
admin.site.register(Result)
admin.site.register(Profile)
