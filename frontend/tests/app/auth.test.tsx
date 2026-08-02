import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import LoginPage, { generateMetadata as loginMetadata } from "../../app/(auth)/login/page";
import SignupPage, { generateMetadata as signupMetadata } from "../../app/(auth)/signup/page";
import AuthLayout from "../../app/(auth)/layout";

describe("(auth) route group", () => {
  it("renders the login page shell with email/password fields and a disabled submit", () => {
    render(<LoginPage />);
    expect(screen.getByRole("heading", { name: /Log in/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/Email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Password/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Log in/i })).toBeDisabled();
    expect(screen.getByRole("link", { name: /Sign up/i })).toHaveAttribute("href", "/signup");
  });

  it("login page is not indexed (robots noindex)", () => {
    const metadata = loginMetadata();
    expect(metadata.robots).toMatchObject({ index: false });
  });

  it("renders the signup page shell with name/email/password fields and a disabled submit", () => {
    render(<SignupPage />);
    expect(screen.getByRole("heading", { name: /Sign up/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/Name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Password/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Sign up/i })).toBeDisabled();
    expect(screen.getByRole("link", { name: /Log in/i })).toHaveAttribute("href", "/login");
  });

  it("signup page is not indexed (robots noindex)", () => {
    const metadata = signupMetadata();
    expect(metadata.robots).toMatchObject({ index: false });
  });

  it("renders the shared auth layout around its children", () => {
    render(
      <AuthLayout>
        <p>child content</p>
      </AuthLayout>,
    );
    expect(screen.getByText("child content")).toBeInTheDocument();
  });
});
