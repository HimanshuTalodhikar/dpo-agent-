# ── ACM TLS Certificate ────────────────────────────────────────────────────────
# Requests a public certificate from AWS ACM and validates via Route 53 DNS.
# Attach to the ALB HTTPS listener on port 443.
# Only created when var.domain_name is set (empty by default = skip TLS).

# Route 53: lookup the hosted zone for the domain
data "aws_route53_zone" "main" {
  count = var.domain_name != "" ? 1 : 0
  name  = var.domain_name
}

# ACM Certificate
resource "aws_acm_certificate" "cloagent" {
  count = var.domain_name != "" ? 1 : 0

  domain_name               = var.domain_name
  validation_method         = "DNS"
  subject_alternative_names = ["*.${var.domain_name}"]

  lifecycle {
    create_before_destroy = true
  }

  tags = merge(var.tags, { Name = "${local.app_name}-cert" })
}

# Route 53: DNS TXT record for ACM to validate domain ownership.
# domain_validation_options is a SET — use tolist() to index it.
resource "aws_route53_record" "cert_validation" {
  count = var.domain_name != "" ? 1 : 0

  zone_id = data.aws_route53_zone.main[0].zone_id
  name    = tolist(aws_acm_certificate.cloagent[0].domain_validation_options)[0].resource_record_name
  type    = tolist(aws_acm_certificate.cloagent[0].domain_validation_options)[0].resource_record_type
  ttl     = 60
  records = [tolist(aws_acm_certificate.cloagent[0].domain_validation_options)[0].resource_record_value]
}

# Wait for ACM to validate via DNS
resource "aws_acm_certificate_validation" "cloagent" {
  count = var.domain_name != "" ? 1 : 0

  certificate_arn         = aws_acm_certificate.cloagent[0].arn
  validation_record_fqdns = [aws_route53_record.cert_validation[0].fqdn]
}

# Expose certificate ARN for use in ecs.tf ALB listener.
# Empty string when domain_name is not set.
locals {
  certificate_arn = var.domain_name != "" ? aws_acm_certificate_validation.cloagent[0].certificate_arn : ""
}
