# Security Policy

## 🔒 Keeping Your Installation Secure

This document outlines security best practices for deploying and maintaining Sulfur Bot.

## ⚠️ Never Commit Sensitive Data

The following files/data should **NEVER** be committed to version control:

### 1. Environment Variables (.env)
- **What:** Your `.env` file contains API keys, database passwords, and Discord tokens
- **Risk:** Anyone with access to your repo can steal your credentials
- **Protection:** Already in `.gitignore` - use `.env.example` as a template

### 2. Database Credentials
- **Files:** `database.ini`, `db_config.json`, any SQL dumps with data
- **Risk:** Database access = full control over bot data
- **Protection:** Use environment variables, never hardcode credentials

### 3. WireGuard VPN Keys
- **Location:** `config/wireguard/`
- **Risk:** VPN keys allow network access to your systems
- **Protection:** Generate keys per-installation, never share private keys

### 4. SSL/TLS Certificates
- **Files:** `*.pem`, `*.key`, `*.crt`
- **Risk:** Certificate compromise can lead to man-in-the-middle attacks
- **Protection:** Generate per-installation, store in secure locations

### 5. Discord Bot Token
- **Location:** `DISCORD_BOT_TOKEN` in `.env`
- **Risk:** Full control of your Discord bot
- **Protection:** Never log, never commit, regenerate if exposed

## 🛡️ Security Best Practices

### For Development

1. **Use .env for all secrets**
   ```bash
   cp .env.example .env
   nano .env  # Edit with your actual values
   ```

2. **Never log sensitive data**
   - Don't print API keys, tokens, or passwords
   - Use `[REDACTED]` in logs instead

3. **Separate development and production**
   - Use different `.env` files for dev/prod
   - Never use production credentials in development

### For Production

1. **Restrict file permissions**
   ```bash
   chmod 600 .env
   chmod 600 config/wireguard/*.key
   ```

2. **Use strong passwords**
   - Database: 16+ characters, random
   - MySQL root: Change from default immediately
   - Never use default passwords like `temp123`

3. **Enable firewall rules**
   - Only expose necessary ports
   - Restrict MySQL to localhost unless needed
   - Use WireGuard VPN for remote access

4. **Regular updates**
   ```bash
   git pull
   source venv/bin/activate
   pip install -r requirements.txt --upgrade
   ```

5. **Database backups**
   - Keep backups in `backups/` (gitignored)
   - Encrypt backups if storing remotely
   - Test restore procedures regularly

### For Public Repositories

If you're forking or contributing:

1. **Before committing:**
   ```bash
   git status
   # Check for .env, *.key, database dumps
   ```

2. **If you accidentally committed secrets:**
   ```bash
   # Remove from history
   git filter-branch --force --index-filter \
     "git rm --cached --ignore-unmatch .env" \
     --prune-empty --tag-name-filter cat -- --all

   # Force push (WARNING: rewrites history)
   git push origin --force --all

   # Regenerate compromised credentials immediately!
   ```

3. **Scan for secrets:**
   ```bash
   # Check what's tracked
   git ls-files | xargs grep -l "password\|token\|secret\|key"
   ```

## 🚨 If Credentials Are Exposed

### Discord Bot Token Compromised

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Select your application
3. Click "Bot" → "Reset Token"
4. Update `.env` with new token
5. Restart the bot

### Database Password Exposed

1. Connect as root:
   ```bash
   mysql -u root -p
   ```

2. Change password:
   ```sql
   ALTER USER 'sulfur_bot_user'@'localhost' IDENTIFIED BY 'new_secure_password';
   FLUSH PRIVILEGES;
   ```

3. Update `.env`

### API Keys Exposed

- **OpenAI:** Revoke at https://platform.openai.com/api-keys
- **Gemini:** Revoke at https://makersuite.google.com/app/apikey
- **Last.fm:** Regenerate at https://www.last.fm/api/account/create

## 📋 Security Checklist

Before deploying to production:

- [ ] `.env` file created and configured
- [ ] `.env` file permissions set to 600
- [ ] Default MySQL root password changed
- [ ] Strong passwords used for all services
- [ ] Firewall configured (only necessary ports open)
- [ ] WireGuard VPN configured (if using remote access)
- [ ] Backups configured and tested
- [ ] Log files rotating (not filling disk)
- [ ] Git repository clean (no sensitive files tracked)
- [ ] Discord bot permissions minimized
- [ ] Regular update schedule established

## 🔍 Auditing

Periodically check for exposed secrets:

```bash
# Check git history for sensitive patterns
git log -p | grep -E "(password|token|secret|key)" | head -20

# Check current working tree
find . -name "*.env" -o -name "*.key" -o -name "*.pem" | grep -v ".example"

# Verify gitignore is working
git status --ignored
```

## 📞 Reporting Security Issues

If you discover a security vulnerability in Sulfur Bot:

1. **DO NOT** open a public issue
2. **DO NOT** commit fixes to public branches
3. Contact the maintainer privately
4. Allow time for patching before disclosure

## 📚 Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Discord Bot Security Best Practices](https://discord.com/developers/docs/topics/oauth2#bot-authorization-flow)
- [Database Security Hardening](https://dev.mysql.com/doc/refman/8.0/en/security-guidelines.html)

---

**Remember:** Security is a process, not a product. Stay vigilant and keep your credentials safe!
