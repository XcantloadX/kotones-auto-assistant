import { useEffect, useMemo, useState } from "react";
import { Form } from "react-bootstrap";
import SectionTitle from "./SectionTitle";
import ProDropdown from "../common/ProDropdown";
import * as optionApi from "../../services/api/options";

type Props = {
  get: (path: string, def?: any) => any;
  set: (path: string) => (e: any) => void;
};

export default function ShopForm({ get, set }: Props) {
  const purchaseEnabled = !!get('data.user_configs.0.options.purchase.enabled', false);
  const moneyEnabled = !!get('data.user_configs.0.options.purchase.money_enabled', false);
  const apEnabled = !!get('data.user_configs.0.options.purchase.ap_enabled', false);

  const moneyItems = (get('data.user_configs.0.options.purchase.money_items', []) as number[]) ?? [];
  const apItems = (get('data.user_configs.0.options.purchase.ap_items', []) as number[]) ?? [];

  const setValue = (path: string) => (val: any) => set(path)({ target: { value: val } });

  const [moneyOptions, setMoneyOptions] = useState<{ label: string; value: number }[]>([]);
  const [apOptions, setApOptions] = useState<{ label: string; value: number }[]>([]);
  useEffect(() => {
    optionApi.getMoneyItems().then(setMoneyOptions).catch(() => {});
    optionApi.getAPItems().then(setApOptions).catch(() => {});
  }, []);

  return (
    <div className="vstack gap-3">
      <SectionTitle
        title="商店购买设置"
        subtitle="设置金币/AP 商店的购买策略"
        enabled={purchaseEnabled}
        showSwitch={true}
        onToggle={set('data.user_configs.0.options.purchase.enabled')}
      />
      
      <SectionTitle
        title="金币购买"
        enabled={moneyEnabled}
        showSwitch={true}
        onToggle={set('data.user_configs.0.options.purchase.money_enabled')}
      />
      <div className="vstack gap-2">
        <ProDropdown<number>
          multiple
          placeholder="选择金币商店购买物品"
          value={moneyItems}
          disabled={!moneyEnabled}
          options={moneyOptions}
          onChange={(vals) => setValue('data.user_configs.0.options.purchase.money_items')(Array.isArray(vals) ? vals : (vals == null ? [] : [vals]))}
        />
        <Form.Check type="switch" label="每日一次免费刷新金币商店" checked={!!get('data.user_configs.0.options.purchase.money_refresh', false)} onChange={set('data.user_configs.0.options.purchase.money_refresh')} />
      </div>
      
      <SectionTitle
        title="AP 购买"
        enabled={apEnabled}
        showSwitch={true}
        onToggle={set('data.user_configs.0.options.purchase.ap_enabled')}
      />
      <div className="vstack gap-2">
        <ProDropdown<number>
          multiple
          placeholder="选择 AP 商店购买物品"
          value={apItems}
          disabled={!apEnabled}
          options={apOptions}
          onChange={(vals) => setValue('data.user_configs.0.options.purchase.ap_items')(Array.isArray(vals) ? vals : (vals == null ? [] : [vals]))}
        />
      </div>
    </div>
  );
} 