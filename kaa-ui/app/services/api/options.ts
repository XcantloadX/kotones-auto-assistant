import { get } from "../http";

export type OptionItem<T = number | string> = { label: string; value: T };

export const getMoneyItems = () => get<OptionItem<number>[]>("/api/v1/options/purchase/money_items");
export const getAPItems = () => get<OptionItem<number>[]>("/api/v1/options/purchase/ap_items"); 