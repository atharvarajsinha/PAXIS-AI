from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import LearnerProfile

User = get_user_model()


def _string_list(value, field_name, max_items=40, max_length=120):
    if value is None:
        return []
    if not isinstance(value, list):
        raise serializers.ValidationError(f'{field_name} must be a list.')
    cleaned = []
    for item in value:
        if not isinstance(item, str):
            raise serializers.ValidationError(f'Every {field_name} entry must be text.')
        item = item.strip()
        if not item:
            continue
        if len(item) > max_length:
            raise serializers.ValidationError(f'Each {field_name} entry must be under {max_length} characters.')
        if item not in cleaned:
            cleaned.append(item)
    if len(cleaned) > max_items:
        raise serializers.ValidationError(f'Please keep {field_name} to {max_items} entries or fewer.')
    return cleaned


class LearnerProfileSerializer(serializers.ModelSerializer):
    completeness = serializers.SerializerMethodField()

    class Meta:
        model = LearnerProfile
        fields = [
            'full_name',
            'headline',
            'experience_level',
            'weekly_hours',
            'interests',
            'objectives',
            'completed_courses',
            'completeness',
            'updated_at',
        ]
        read_only_fields = ['completeness', 'updated_at']

    def get_completeness(self, obj):
        return obj.completeness()

    def validate_interests(self, value):
        return _string_list(value, 'interests')

    def validate_objectives(self, value):
        return _string_list(value, 'objectives')

    def validate_completed_courses(self, value):
        return _string_list(value, 'completed courses', max_length=160)

    def validate_weekly_hours(self, value):
        if value > 168:
            raise serializers.ValidationError('There are only 168 hours in a week.')
        return value


class UserSerializer(serializers.ModelSerializer):
    profile = LearnerProfileSerializer(source='learner_profile', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'date_joined', 'profile']
        read_only_fields = fields


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(write_only=True, max_length=128, trim_whitespace=False)
    full_name = serializers.CharField(max_length=120, required=False, allow_blank=True)

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists() or User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError('An account with this email already exists.')
        if len(value) > 150:
            raise serializers.ValidationError('That email address is too long.')
        return value

    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        return value

    def create(self, validated_data):
        email = validated_data['email']
        # Django's User.username is the required natural key; the email doubles
        # as the username so learners only ever type one identifier.
        user = User.objects.create_user(
            username=email,
            email=email,
            password=validated_data['password'],
        )
        full_name = (validated_data.get('full_name') or '').strip()
        if full_name:
            profile = user.learner_profile
            profile.full_name = full_name
            profile.save(update_fields=['full_name', 'updated_at'])
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(write_only=True, max_length=128, trim_whitespace=False)

    def validate(self, attrs):
        email = attrs['email'].strip().lower()
        user = authenticate(
            request=self.context.get('request'),
            username=email,
            password=attrs['password'],
        )
        if user is None:
            # Deliberately identical for unknown email and wrong password so the
            # endpoint cannot be used to enumerate registered addresses.
            raise serializers.ValidationError({'detail': 'Invalid email or password.'})
        if not user.is_active:
            raise serializers.ValidationError({'detail': 'This account has been deactivated.'})
        attrs['user'] = user
        return attrs


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, max_length=128, trim_whitespace=False)

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Current password is incorrect.')
        return value

    def validate_new_password(self, value):
        try:
            validate_password(value, self.context['request'].user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        return value
