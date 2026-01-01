from rest_framework import serializers
from .models import Article, ArticleVersion, ActivityLog
from apps.users.serializers import UserSerializer


class ArticleVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArticleVersion
        fields = '__all__'


class ActivityLogSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    
    class Meta:
        model = ActivityLog
        fields = '__all__'
    
    def get_user_name(self, obj):
        return obj.user.get_full_name() if obj.user else 'System'


class ArticleSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    journal_name = serializers.SerializerMethodField()
    versions = ArticleVersionSerializer(many=True, read_only=True)
    activity_logs = ActivityLogSerializer(many=True, read_only=True)
    analytics = serializers.SerializerMethodField()
    
    class Meta:
        model = Article
        fields = '__all__'
        read_only_fields = ('id', 'submission_date', 'views_count', 'downloads_count', 'citations_count')
    
    def get_author_name(self, obj):
        return obj.author.get_full_name()
    
    def get_journal_name(self, obj):
        return obj.journal.name
    
    def get_analytics(self, obj):
        return {
            'views': obj.views_count,
            'downloads': obj.downloads_count,
            'citations': obj.citations_count
        }


class CreateArticleSerializer(serializers.ModelSerializer):
    journal = serializers.CharField(required=False)  # Allow string ID for journal
    
    class Meta:
        model = Article
        fields = ('title', 'abstract', 'keywords', 'journal', 'final_pdf_path', 
                  'additional_document_path', 'page_count', 'fast_track')
    
    def validate(self, attrs):
        # Check if journal is provided
        if 'journal' not in attrs or attrs['journal'] is None or attrs['journal'] == '':
            # Check if this is a book publication by looking at the title
            title = attrs.get('title', '')
            if '[KITOB]' in title or 'book' in title.lower():
                # For book publications, assign a default journal
                from apps.journals.models import Journal
                try:
                    # Try to find a book-related journal first
                    book_journal = Journal.objects.filter(name__icontains='book').first()
                    if book_journal:
                        attrs['journal'] = book_journal
                    else:
                        # Use the first available journal as default
                        default_journal = Journal.objects.first()
                        if default_journal:
                            attrs['journal'] = default_journal
                        else:
                            # If no journals exist, raise validation error
                            raise serializers.ValidationError({'journal': 'No journals available. Please create a journal first.'})
                except Exception as e:
                    raise serializers.ValidationError({'journal': f'Error assigning journal: {str(e)}'})
            else:
                # For regular articles, journal must be provided
                raise serializers.ValidationError({'journal': 'Journal is required for article submission.'})
        else:
            # If journal is provided as a string ID, convert it to a Journal object
            journal_id = attrs['journal']
            if isinstance(journal_id, str):
                from apps.journals.models import Journal
                try:
                    journal_obj = Journal.objects.get(id=journal_id)
                    attrs['journal'] = journal_obj
                except Journal.DoesNotExist:
                    raise serializers.ValidationError({'journal': f'Journal with id {journal_id} does not exist.'})
                except Exception as e:
                    raise serializers.ValidationError({'journal': f'Invalid journal ID: {str(e)}'})
        return attrs
    
    def create(self, validated_data):
        validated_data['author'] = self.context['request'].user
        # Only set status to 'Draft' if it's not already provided
        if 'status' not in validated_data or not validated_data['status']:
            validated_data['status'] = 'Draft'
        return super().create(validated_data)
