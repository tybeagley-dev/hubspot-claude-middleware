"""
Property mappings for translating HubSpot properties to more readable formats
"""

PROPERTY_MAPPINGS = {
    # Company properties
    "name": "Company Name",
    "domain": "Website Domain",
    "industry": "Industry", 
    "city": "City",
    "state": "State",
    "country": "Country",
    "numberofemployees": "Number of Employees",
    "annualrevenue": "Annual Revenue",
    "createdate": "Created Date",
    "hs_lastmodifieddate": "Last Modified Date",
    "hs_object_id": "Company ID",
    "description": "Description",
    "phone": "Phone Number",
    "website": "Website",
    "type": "Company Type",
    "founded_year": "Founded Year",
    "twitterhandle": "Twitter Handle",
    "facebookfans": "Facebook Fans",
    "linkedin_company_page": "LinkedIn Company Page",
    "lifecyclestage": "Lifecycle Stage",
    "hubspot_owner_id": "Owner ID",
    "hubspot_owner_assigneddate": "Owner Assigned Date",
    "web_technologies": "Web Technologies",
    "total_money_raised": "Total Money Raised",
    "recent_deal_amount": "Recent Deal Amount",
    "recent_deal_close_date": "Recent Deal Close Date",
    "num_associated_contacts": "Number of Associated Contacts",
    "num_associated_deals": "Number of Associated Deals",
    "timezone": "Timezone",
    "hs_lead_status": "Lead Status",
    "hs_analytics_source": "Analytics Source",
    "hs_analytics_first_touch_converting_campaign": "First Touch Converting Campaign",
    "hs_analytics_last_touch_converting_campaign": "Last Touch Converting Campaign",
    
    # Custom property mappings
    "account_status": "Account Status",
    "subscription_type": "Subscription Type",
    "contract_start_date": "Contract Start Date",
    "contract_end_date": "Contract End Date",
    "monthly_recurring_revenue": "Monthly Recurring Revenue",
    "customer_tier": "Customer Tier",
    "support_level": "Support Level",
    "integration_status": "Integration Status",
    "onboarding_status": "Onboarding Status",
    "health_score": "Health Score",
    "last_activity_date": "Last Activity Date",
    "renewal_date": "Renewal Date",
    "churn_risk": "Churn Risk",
    "expansion_opportunity": "Expansion Opportunity"
}

# Value mappings for specific properties
VALUE_MAPPINGS = {
    "account_status": {
        "cancelled": "Pending Cancellation",
        "active": "Active",
        "inactive": "Inactive",
        "trial": "Trial",
        "suspended": "Suspended",
        "pending": "Pending Setup"
    },
    "lifecyclestage": {
        "subscriber": "Subscriber",
        "lead": "Lead", 
        "marketingqualifiedlead": "Marketing Qualified Lead",
        "salesqualifiedlead": "Sales Qualified Lead",
        "opportunity": "Opportunity",
        "customer": "Customer",
        "evangelist": "Evangelist",
        "other": "Other"
    },
    "hs_lead_status": {
        "NEW": "New",
        "OPEN": "Open",
        "IN_PROGRESS": "In Progress",
        "CONNECTED": "Connected",
        "BAD_TIMING": "Bad Timing",
        "UNQUALIFIED": "Unqualified",
        "ATTEMPTED_TO_CONTACT": "Attempted to Contact",
        "NOT_QUALIFIED": "Not Qualified"
    },
    "customer_tier": {
        "enterprise": "Enterprise",
        "professional": "Professional", 
        "standard": "Standard",
        "basic": "Basic",
        "startup": "Startup"
    },
    "churn_risk": {
        "high": "High Risk",
        "medium": "Medium Risk",
        "low": "Low Risk",
        "none": "No Risk"
    }
}

# Reverse mappings for API queries
REVERSE_PROPERTY_MAPPINGS = {v: k for k, v in PROPERTY_MAPPINGS.items()}
REVERSE_VALUE_MAPPINGS = {
    prop: {v: k for k, v in values.items()} 
    for prop, values in VALUE_MAPPINGS.items()
}