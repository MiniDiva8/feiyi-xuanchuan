# Platform API v1
All endpoints below are prefixed /api. JSON, cookie session HttpOnly; credentials same-origin. Business endpoints prefixed /workspaces/{workspace_id}; all IDs opaque strings. Errors {detail:string}; lists are JSON arrays, entities JSON objects (no envelope). Monetary values in yuan, nonnegative. Server validates authenticated workspace membership on every private route. owner/editor may edit; owner/reviewer may approve. Unauthenticated 401, foreign workspace 403/404, wrong workflow 409, validation 422.

## Auth
POST /auth/register {name,email,password,workspace_name} -> {user:{id,name,email},workspaces:Workspace[]}; min password 10 chars. Creates empty workspace, sets cookie.
POST /auth/login {email,password} -> same. GET /auth/me -> same. POST /auth/logout {} -> {ok:true}.
Workspace={id,name,description,role,created_at}. GET /workspaces -> Workspace[]. POST /workspaces {name,description?} -> Workspace.

## Workspace resources
GET /overview -> {stats:{campaigns,pending_review,publications,revenue,spend,orders,registrations,impressions,interactions},trends:[{date,impressions,revenue}],recent_campaigns:Campaign[],activity:Audit[],connections:{ai_configured:boolean,publishing:'manual',checkout:'external'}}.
GET /settings -> {ai_configured:boolean,ai_model:string,publishing:'manual',checkout:'external'} (never secrets).
GET /knowledge -> Knowledge[]. POST /knowledge {title,content,source,usage_scope:'marketing'|'internal',confirmed:boolean,kind:'fact'|'brand'|'material',file_id?:string} -> Knowledge. PATCH /knowledge/{id} same partial fields -> Knowledge. DELETE /knowledge/{id} -> {ok:true}. Knowledge adds id,workspace_id,created_at. Generation uses only current-workspace confirmed marketing knowledge.
POST /files multipart form file -> {id,name,size,mime_type}; GET /files/{id} -> attachment bytes; uploads max 10MiB; no executable/html/svg upload.
GET /offerings -> Offering[]. POST /offerings {kind:'product'|'course',name,description,price:number,quantity:int,location:string,delivery:string,conversion_url:string} -> Offering. PATCH /offerings/{id} partial same -> Offering. Offering adds id,workspace_id,created_at. conversion_url requires http(s). Quantity stock or seats; no platform checkout/payment.
GET /campaigns -> Campaign[]. POST /campaigns {name,objective:'sales'|'registration'|'awareness',audience,start_date:'YYYY-MM-DD',end_date,budget:number,channels:string[],offering_id?:string|null,notes:string} -> Campaign. GET /campaigns/{id} -> Campaign. Campaign adds id,workspace_id,status,previous_campaign_id?,created_at.
GET /campaigns/{id}/plans -> Plan[]. POST /campaigns/{id}/plans/generate {instructions?:string} -> Plan.
Plan={id,workspace_id,campaign_id,version,status:'draft'|'approved'|'rejected',generation_mode:'template'|'ai',content:{theme,summary,audience,channels:[{channel,reason,content_ideas:string[]}],schedule:[{day,action,channel}],budget:[{item,amount}],warnings:string[],evidence:[{id,title,source}]},created_at}.
POST /plans/{id}/revise {instructions:string,content?:object} -> NEW Plan version, draft. POST /plans/{id}/approve {} -> Plan. POST /plans/{id}/reject {reason:string} -> Plan.
GET /campaigns/{id}/assets -> Asset[]. POST /campaigns/{id}/assets/generate {plan_id,channel,kind:'copy'|'poster'|'script',instructions?:string} -> Asset; requires current approved plan.
Asset={id,workspace_id,campaign_id,plan_id,version,channel,kind,title,body,content:object,status:'draft'|'approved'|'rejected',checks:[{level:'warning'|'info'|'error',message:string}],generation_mode:'template'|'ai',created_at}.
POST /assets/{id}/revise {title?:string,body:string} -> NEW Asset version, draft; do not mutate approved version. POST /assets/{id}/approve {} -> Asset. POST /assets/{id}/reject {reason:string} -> Asset.
GET /assets/{id}/export?format=txt|html|svg -> approved attachment. Approved content must still have confirmed/allowed source snapshot and valid offering. Latest versions only publishable, historical records preserved.
GET /publications -> Publication[]. POST /publications {asset_id,channel,url:string,published_at:ISOdatetime,external_id?:string} -> Publication; requires approved latest asset/plan; validates http(s) work URL. Adds id,workspace_id,campaign_id,plan_id,asset_id,created_at. Manual registration is not API publishing.
GET /metrics?campaign_id optional -> Metric[]. POST /metrics MetricInput -> Metric.
MetricInput={campaign_id,publication_id?:string|null,date:'YYYY-MM-DD',channel,source,external_id?:string,attribution:'known'|'unknown',impressions:0,views:0,reads:0,interactions:0,inquiries:0,reservations:0,leads:0,orders:0,revenue:0,refunds:0,registrations:0,checkins:0,spend:0}. Numeric fields default zero, nonnegative; refunds<=revenue, checkins<=registrations; integer counts. A publication must belong to same campaign/workspace.
POST /metrics/preview {csv:string} -> {rows:MetricInput[],errors:[{row:number,message:string}],duplicates:number,valid_rows:number}. CSV headers use MetricInput keys; optional fields/numerics default. Frontend supplies downloadable template with campaign ID selected.
POST /metrics/import {csv:string} -> {imported:number,duplicates:number}; validates whole input before atomic insert; dedupe by workspace + external_id if provided, otherwise normalized row hash. Manual duplicate yields 409.
GET /analytics?campaign_id optional -> {stats:{impressions,views,reads,interactions,inquiries,reservations,leads,orders,revenue,refunds,net_revenue,registrations,checkins,spend,unknown_revenue},trends:[{date,impressions,revenue,spend}],channels:[{channel,impressions,interactions,orders,revenue,spend}],records:number}.
GET /campaigns/{id}/reviews -> Review[]. POST /campaigns/{id}/reviews/generate {} -> Review={id,campaign_id,generation_mode,content:{facts:[{statement,evidence}],hypotheses:[{statement,validation}],suggestions:[{action,metric}],limitations:string[]},created_at}.
POST /campaigns/{id}/next-round {name?:string} -> NEW Campaign with previous_campaign_id and draft status; no inherited approval.
GET /tasks -> Task[]={id,kind,status:'queued'|'running'|'succeeded'|'failed',generation_mode?,error?,usage?:object,created_at}; POST /tasks/{id}/retry {} -> Task/result (bounded attempts).
GET /audit -> Audit[]={id,action,entity_type,entity_id,actor_name,created_at,details?:object}.
GET /members -> [{user_id,name,email,role}]; POST /members {email,role:'editor'|'reviewer'} -> member; owner only, existing registered accounts, does not send email. No public self-enrollment into an existing workspace.

## AI Python interface
Module import marketing_ai.engine available through PYTHONPATH services/marketing-ai. Functions generate_plan(context:dict), generate_asset(context:dict), build_review(context:dict), check_content(text:str,context:dict) -> dict/list.
context={workspace:{id,name},campaign:{...},offering:dict|null,knowledge:[{id,title,content,source,usage_scope,confirmed}],plan:dict|null,kind?,channel?,instructions?,analytics?:dict}.
generate_plan -> {content:Plan.content,generation_mode:'template'|'ai',usage:dict}.
generate_asset -> {title,body,content:dict,checks:list,generation_mode,usage:dict}.
build_review -> {content:Review.content,generation_mode,usage:dict}.
check_content -> [{level,message}]. Only confirmed marketing knowledge is used; insufficient knowledge warns and does not invent heritage credentials. AI environment: MARKETING_AI_BASE_URL (default https://api.openai.com/v1), MARKETING_AI_API_KEY, MARKETING_AI_MODEL, MARKETING_AI_TIMEOUT_SECONDS, MARKETING_AI_MAX_OUTPUT_TOKENS. No key => explicitly labeled template. Failed configured model raises bounded RuntimeError, not silent fake success.

## Integration additions
PATCH /workspaces/{workspace_id}/campaigns/{id} accepts partial CampaignInput, returns Campaign; retains IDs and history, prior approvals become stale if the brief changed. New-round campaigns can update budget and dates before regeneration.
CSV rows sharing an external_id but differing normalized data are conflicts, not duplicates: preview returns row errors; import is rejected atomically. Only exact normalized duplicates are skipped.
Sales/registration approval/export/publication require a matching sellable product/course and positive capacity. Asset channel must appear in both the approved plan and campaign channels.
