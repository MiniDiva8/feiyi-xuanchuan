import { useState } from "react";
import { ArrowUpRight, ShieldCheck, Layers, BarChart3 } from "lucide-react";
import { Form, Notice } from "../components/UI";
import { post } from "../api";
import type { Session } from "../types";
export default function Auth({
  onSuccess,
}: {
  onSuccess: (s: Session) => void;
}) {
  const [register, setRegister] = useState(false);
  return (
    <main className="auth">
      <section className="auth-story">
        <div className="brand">
          <span className="brand-seal">承</span>
          <div>
            承艺<span>HERITAGE STUDIO</span>
          </div>
        </div>
        <div className="story-copy">
          <div className="eyebrow">让好手艺，被更多人看见</div>
          <h1>
            一门手艺。
            <br />
            一段故事。
            <br />
            <em>下一次相遇。</em>
          </h1>
          <p>
            从真实的文化资料出发，协作策划、打磨内容，
            <br />
            把每一次传播，变成可以回看的经营积累。
          </p>
          <div className="story-lines">
            <span>01 / 资料有据</span>
            <span>02 / 内容可审</span>
            <span>03 / 经营可循</span>
          </div>
        </div>
        <div className="craft-art" aria-hidden="true">
          <i />
          <i />
          <i />
          <i />
          <i />
          <i />
          <span>艺</span>
        </div>
        <footer>
          为传承而记录 · 为经营而创造 <ArrowUpRight size={18} />
        </footer>
      </section>
      <section className="auth-form">
        <div className="auth-inner">
          <span className="eyebrow">商家工作台</span>
          <h2>{register ? "从你的第一门手艺开始" : "欢迎回来"}</h2>
          <p>
            {register
              ? "创建账号与独立商家空间，开始建立营销档案。"
              : "登录，继续打磨属于你的品牌故事。"}
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
                    { key: "name", label: "你的姓名", required: true },
                    {
                      key: "workspace_name",
                      label: "商家 / 品牌名称",
                      required: true,
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
                help: "至少 10 个字符",
              },
            ]}
            submitLabel={register ? "创建商家空间" : "登录工作台"}
            onSubmit={async (d) =>
              onSuccess(
                await post<Session>(
                  "/auth/" + (register ? "register" : "login"),
                  d,
                ),
              )
            }
          />
          <Notice>
            <ShieldCheck size={15} />{" "}
            每个商家拥有独立的数据空间；生成内容经过审核后才能导出。
          </Notice>
          <div className="auth-foot">
            <Layers size={15} />
            资料与版本留痕 <span />
            <BarChart3 size={15} /> 真实数据复盘
          </div>
        </div>
        <div className="auth-bottom">承艺 · 非遗商家营销协作平台</div>
      </section>
    </main>
  );
}
