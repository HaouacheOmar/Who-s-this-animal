from django.contrib.auth.tokens import PasswordResetTokenGenerator, default_token_generator


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    key_salt = "accounts.EmailVerificationTokenGenerator"

    def _make_hash_value(self, user, timestamp):
        # Including email_verified kills the link once the email is verified.
        return f"{user.pk}{user.email_verified}{timestamp}"


verification_token = EmailVerificationTokenGenerator()
reset_token = default_token_generator  # hashes password + last_login: dies once the password changes
