"""Forms used by the website views."""
from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import Product, Review, Store, User


class RegistrationForm(UserCreationForm):
    """Sign-up form that also asks whether the user is a vendor or a buyer."""

    role = forms.ChoiceField(choices=User.ROLE_CHOICES, label="Register as")

    class Meta:
        """Fields shown on the registration page."""

        model = User
        fields = ("username", "email", "role")

    def save(self, commit=True):
        """Create the user and store the chosen role.

        Args:
            commit: Save to the database when True.

        Returns:
            The new User.
        """
        user = super().save(commit=False)
        user.role = self.cleaned_data["role"]
        if commit:
            user.save()
        return user


class StoreForm(forms.ModelForm):
    """Create or edit a store."""

    class Meta:
        """Model and fields for the store form."""

        model = Store
        fields = ("name", "description")


class ProductForm(forms.ModelForm):
    """Create or edit a product."""

    class Meta:
        """Model and fields for the product form."""

        model = Product
        fields = ("name", "description", "price", "stock")


class ReviewForm(forms.ModelForm):
    """Leave a review: a 1-5 rating and an optional comment."""

    rating = forms.IntegerField(min_value=1, max_value=5)

    class Meta:
        """Model and fields for the review form."""

        model = Review
        fields = ("rating", "comment")


class CartAddForm(forms.Form):
    """Quantity to add to the cart."""

    quantity = forms.IntegerField(min_value=1, max_value=999, initial=1)


class PasswordResetRequestForm(forms.Form):
    """Ask for the email address of the account to reset."""

    email = forms.EmailField()
