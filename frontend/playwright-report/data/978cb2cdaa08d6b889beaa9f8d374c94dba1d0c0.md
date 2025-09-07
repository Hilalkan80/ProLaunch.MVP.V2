# Page snapshot

```yaml
- generic [active] [ref=e1]:
  - generic [ref=e4]:
    - generic [ref=e5]:
      - heading "Welcome to ProLaunch" [level=2] [ref=e6]
      - paragraph [ref=e7]: Please sign in or create an account to continue
    - generic [ref=e8]:
      - link "Sign in" [ref=e9] [cursor=pointer]:
        - /url: /auth/signin
      - link "Create account" [ref=e10] [cursor=pointer]:
        - /url: /auth/signup
  - alert [ref=e11]
```