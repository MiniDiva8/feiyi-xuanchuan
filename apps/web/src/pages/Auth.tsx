import { useState } from "react";
import { ArrowUpRight, ShieldCheck, Layers, CheckCircle2 } from "lucide-react";
import { Form } from "../components/UI";
import { post } from "../api";
import type { Session } from "../types";
export default function Auth({
  onSuccess,
}: {
  onSuccess: (session: Session) => void;
}) {
  const [register, setRegister] = useState(false);
  return (
    <main className="auth">
      <section className="auth-story">
        <div className="auth-photo" aria-hidden="true" />
        <div className="brand">
          <span className="brand-seal">承</span>
          <div>
            承艺<span>HERITAGE STUDIO</span>
          </div>
        </div>
        <span className="auth-edition">为好手艺，留一份长久的经营。</span>
        <div className="story-copy">
          <span className="eyebrow">CRAFTED WITH PURPOSE</span>
          <h1>
            让好手艺，
            <br />
            被看见。
          </h1>
          <p>
            把真实的品牌故事，变成有序的营销行动。
            <br />
            从一份资料，到下一次相遇。
          </p>
          <div className="story-lines">
            <span>资料有据</span>
            <i />
            <span>内容可审</span>
            <i />
            <span>经营可循</span>
          </div>
        </div>
        <footer>
          <span>非遗商家的日常经营伙伴</span>
          <ArrowUpRight size={20} />
        </footer>
        <span className="art-caption">工艺氛围示意 · 原创生成图</span>
      </section>
      <section className={"auth-form " + (register ? "auth-register" : "")}>
        <div className="auth-inner">
          <div className="auth-form-mark">
            <span className="brand-seal">承</span>
            <span>承艺 · 商家工作台</span>
          </div>
          <span className="eyebrow">YOUR NEXT CHAPTER</span>
          <h2>{register ? "从你的品牌开始" : "欢迎回到承艺"}</h2>
          <p>
            {register
              ? "创建账号与独立商家空间，开始记录你的第一份经营积累。"
              : "继续你的创作与经营，让每一步都清楚可循。"}
          </p>
          <div className="auth-tabs">
            <button
              className={!register ? "active" : ""}
              onClick={() => setRegister(false)}
            >
              账号登录
            </button>
            <button
              className={register ? "active" : ""}
              onClick={() => setRegister(true)}
            >
              注册商家
            </button>
          </div>
          <Form
            key={String(register)}
            fields={[
              ...(register
                ? [
                    {
                      key: "name",
                      label: "昵称",
                      required: true,
                      placeholder: "在工作台中显示的称呼",
                    },
                    {
                      key: "workspace_name",
                      label: "商家 / 品牌名称",
                      required: true,
                      placeholder: "例如：青山手作工坊",
                    },
                  ]
                : []),
              {
                key: "email",
                label: "邮箱地址",
                type: "email",
                required: true,
                placeholder: "name@example.com",
              },
              {
                key: "password",
                label: "密码",
                type: "password",
                required: true,
                placeholder: "请输入至少10个字符",
                help: "至少 10 个字符",
              },
            ]}
            submitLabel={register ? "创建商家空间" : "登录工作台"}
            onSubmit={async (values) =>
              onSuccess(
                await post<Session>(
                  "/auth/" + (register ? "register" : "login"),
                  values,
                ),
              )
            }
          />
          <div className="auth-assurance">
            <ShieldCheck size={18} />
            <span>每个商家拥有独立空间，私有资料与经营记录按商家隔离。</span>
          </div>
          <div className="auth-foot">
            <Layers size={15} />
            资料与版本留痕 <span />
            <CheckCircle2 size={15} />
            商家确认后导出
          </div>
        </div>
        <div className="auth-bottom">
          承艺 HERITAGE STUDIO <span>有据可依，有序向前。</span>
        </div>
      </section>
    </main>
  );
}
